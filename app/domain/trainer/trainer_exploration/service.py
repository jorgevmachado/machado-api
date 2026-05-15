from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.service import CacheService
from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.trainer.my_pokemon.schema import MyPokemonSchema
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.domain.trainer.schema import TrainerSchema
from app.domain.trainer.trainer_exploration.business import (
    build_pokeball_reward,
    choose_event_type,
    choose_wild_pokemon,
    resolve_initial_active_encounter,
    validate_party_selection,
)
from app.domain.trainer.trainer_exploration.repository import TrainerExplorationRepository
from app.domain.trainer.trainer_exploration.schema import (
    ExplorationEventSchema,
    SelectTrainerEncounterSchema,
    TrainerEncounterSchema,
    TrainerHomeSchema,
    TrainerPartyMemberSchema,
    UpdateTrainerPartySchema,
)
from app.models import ExplorationEventTypeEnum, MyPokemon, Trainer, TrainerEncounter, User
from app.models.common import utcnow
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class TrainerExplorationService(
    BaseService[TrainerExplorationRepository, TrainerEncounter, TrainerEncounterSchema]
):
    def __init__(
        self,
        repository: TrainerExplorationRepository,
        trainer_service: TrainerService | None = None,
    ) -> None:
        super().__init__(
            alias="TrainerEncounters",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="TrainerExplorationService",
                operation="trainer_exploration",
            ),
            schema_class=TrainerEncounterSchema,
            cache_prefix="trainer",
        )
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        self.home_cache_service = CacheService(
            alias="TrainerHome",
            prefix="trainer",
            logger_params=self.logger_params,
            schema_class=TrainerHomeSchema,
        )
        self.encounter_cache_service = self.cache_service
        self.party_cache_service = CacheService(
            alias="TrainerParty",
            prefix="trainer",
            logger_params=self.logger_params,
            schema_class=TrainerPartyMemberSchema,
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerExplorationRepository(session))

    def _home_key(self, trainer_id: str) -> str:
        return self.home_cache_service.cache.build_key("trainer", "home", trainer_id)

    def _party_key(self, trainer_id: str) -> str:
        return self.party_cache_service.cache.build_key("trainer", "party", trainer_id)

    async def _invalidate_cache(self, trainer_id: str) -> None:
        await self.home_cache_service.cache.delete_cache(self._home_key(trainer_id))
        await self.encounter_cache_service.cache.delete_cache(
            self.encounter_cache_service.build_key_list(
                FilterPage.build(trainer_id=trainer_id)
            )
        )
        await self.party_cache_service.cache.delete_cache(self._party_key(trainer_id))

    async def _get_trainer_or_404(self, current_user: User) -> Trainer:
        trainer = await self.trainer_service.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer not found",
            )
        return trainer

    async def initialize_for_trainer(
        self,
        *,
        trainer_id,
        starter_pokemon_name: str,
        commit: bool = True,
    ):
        encounters = await self.repository.list_encounters_for_pokemon(starter_pokemon_name)
        active_encounter = resolve_initial_active_encounter(encounters)
        entities = await self.repository.create_known_encounters(
            trainer_id=trainer_id,
            encounters=encounters,
            active_encounter_id=active_encounter.id if active_encounter else None,
        )
        if commit:
            await self.repository.session.commit()
            await self._invalidate_cache(str(trainer_id))
        result = []
        for entity in entities:
            fresh = await self.repository.find_by(
                trainer_id=trainer_id,
                id=entity.id,
            )
            if fresh is not None:
                result.append(fresh)
        return result

    async def list_encounters(self, current_user: User) -> list[TrainerEncounterSchema]:
        trainer = await self._get_trainer_or_404(current_user)
        return await super().list_all_cached(trainer_id=str(trainer.id))

    async def select_active_encounter(
        self,
        current_user: User,
        payload: SelectTrainerEncounterSchema,
    ) -> TrainerEncounterSchema:
        trainer = await self._get_trainer_or_404(current_user)
        entity = await self.repository.find_by(
            trainer_id=trainer.id,
            id=payload.encounter_id,
        )
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer encounter not found",
            )
        await self.repository.deactivate_all_encounters(trainer.id)
        entity.is_active = True
        await self.repository.session.commit()
        await self._invalidate_cache(str(trainer.id))
        fresh = await self.repository.find_by(
            trainer_id=trainer.id,
            id=payload.encounter_id,
        )
        if fresh is None:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Could not load active trainer encounter",
            )
        return self.to_encounter_schema(fresh)

    async def update_party(
        self,
        current_user: User,
        payload: UpdateTrainerPartySchema,
    ) -> list[TrainerPartyMemberSchema]:
        trainer = await self._get_trainer_or_404(current_user)
        validate_party_selection(payload.my_pokemon_ids)
        my_pokemons = await self.repository.list_owned_my_pokemon(
            trainer.id,
            payload.my_pokemon_ids,
        )
        if len(my_pokemons) != len(payload.my_pokemon_ids):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Trainer party contains invalid Pokemon",
            )
        my_pokemon_by_id = {entity.id: entity for entity in my_pokemons}
        ordered_party: list[MyPokemon] = [
            my_pokemon_by_id[my_pokemon_id] for my_pokemon_id in payload.my_pokemon_ids
        ]
        await self.repository.soft_delete_active_party(trainer.id, utcnow())
        await self.repository.create_party(
            trainer_id=trainer.id,
            my_pokemons=ordered_party,
        )
        await self.repository.session.commit()
        await self._invalidate_cache(str(trainer.id))
        return await self.get_party(current_user)

    async def get_party(self, current_user: User) -> list[TrainerPartyMemberSchema]:
        trainer = await self._get_trainer_or_404(current_user)
        key = self._party_key(str(trainer.id))
        cached = await self.party_cache_service.get_list(key)
        if cached:
            return cached
        entities = await self.repository.list_active_party(trainer.id)
        serialized = [self.to_party_schema(entity) for entity in entities]
        await self.party_cache_service.set_list(key, serialized)
        return serialized

    async def walk(self, current_user: User) -> ExplorationEventSchema:
        trainer = await self._get_trainer_or_404(current_user)
        active_encounter = await self.repository.find_active_trainer_encounter(trainer.id)
        if active_encounter is None:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Trainer has no active encounter",
            )

        event_type = choose_event_type()
        payload: dict = {}

        if event_type == ExplorationEventTypeEnum.WILD_POKEMON:
            pokemon = choose_wild_pokemon(active_encounter.pokemon_encounter.pokemons)
            payload = {
                "pokemon_id": str(pokemon.id),
                "encounter_id": str(active_encounter.pokemon_encounter.id),
            }
        else:
            reward = build_pokeball_reward()
            trainer.pokeballs += reward
            payload = {
                "pokeballs_found": reward,
                "trainer_pokeballs": trainer.pokeballs,
            }

        entity = await self.repository.create_event(
            trainer_id=trainer.id,
            event_type=event_type,
            payload=payload,
        )
        await self.repository.session.commit()
        await self._invalidate_cache(str(trainer.id))
        return self.to_event_schema(entity, active_encounter=active_encounter)

    async def get_home(self, current_user: User) -> TrainerHomeSchema:
        trainer = await self._get_trainer_or_404(current_user)
        key = self._home_key(str(trainer.id))
        cached = await self.home_cache_service.get_one(key)
        if cached:
            return cached
        active_encounter = await self.repository.find_active_trainer_encounter(trainer.id)
        party = await self.repository.list_active_party(trainer.id)
        latest_discoveries = await self.repository.list_latest_discoveries(trainer.id)
        serialized = TrainerHomeSchema(
            trainer=TrainerSchema.model_validate(trainer),
            active_encounter=self.to_encounter_schema(active_encounter)
            if active_encounter
            else None,
            party=[self.to_party_schema(entity) for entity in party],
            latest_discoveries=[
                PokedexSchema.model_validate(entry) for entry in latest_discoveries
            ],
        )
        await self.home_cache_service.set_one(key, serialized)
        return serialized

    @staticmethod
    def to_encounter_schema(entity) -> TrainerEncounterSchema:
        return TrainerEncounterSchema.model_validate(entity)

    @staticmethod
    def to_party_schema(entity) -> TrainerPartyMemberSchema:
        return TrainerPartyMemberSchema.model_validate(entity)

    @staticmethod
    def to_event_schema(entity, active_encounter=None) -> ExplorationEventSchema:
        payload = entity.payload or {}
        pokemon = None
        encounter = active_encounter.pokemon_encounter if active_encounter else None
        if (
            entity.event_type == ExplorationEventTypeEnum.WILD_POKEMON
            and active_encounter is not None
        ):
            pokemon_id = payload.get("pokemon_id")
            pokemon = next(
                (
                    candidate
                    for candidate in active_encounter.pokemon_encounter.pokemons
                    if str(candidate.id) == pokemon_id
                ),
                None,
            )
        return ExplorationEventSchema(
            id=entity.id,
            event_type=entity.event_type,
            created_at=entity.created_at,
            pokemon=pokemon,
            encounter=encounter,
            pokeballs_found=payload.get("pokeballs_found"),
            trainer_pokeballs=payload.get("trainer_pokeballs"),
        )

    @staticmethod
    def to_my_pokemon_schema(entity: MyPokemon) -> MyPokemonSchema:
        return MyPokemonSchema.model_validate(entity)
