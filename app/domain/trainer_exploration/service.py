from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.service import CacheService
from app.core.logging import LoggingParams
from app.domain.my_pokemon.schema import MyPokemonOwnedMoveSchema, MyPokemonSchema
from app.domain.pokedex.service import PokedexService
from app.domain.trainer.schema import TrainerSchema
from app.domain.trainer_exploration.business import (
    build_pokeball_reward,
    choose_event_type,
    choose_wild_pokemon,
    resolve_initial_active_encounter,
    validate_party_selection,
)
from app.domain.trainer_exploration.repository import TrainerExplorationRepository
from app.domain.trainer_exploration.schema import (
    ExplorationEventSchema,
    SelectTrainerEncounterSchema,
    TrainerEncounterSchema,
    TrainerHomeSchema,
    TrainerPartyMemberSchema,
    UpdateTrainerPartySchema,
)
from app.models import ExplorationEventTypeEnum, MyPokemon, Trainer, User
from app.models.common import utcnow

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class TrainerExplorationService:
    def __init__(
        self,
        repository: TrainerExplorationRepository,
        trainer_service: TrainerService | None = None,
    ) -> None:
        self.repository = repository
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        logger_params = LoggingParams(
            logger=logger,
            service="TrainerExplorationService",
            operation="trainer_exploration",
        )
        self.home_cache_service = CacheService(
            alias="TrainerHome",
            prefix="trainer",
            logger_params=logger_params,
            schema_class=TrainerHomeSchema,
        )
        self.encounter_cache_service = CacheService(
            alias="TrainerEncounters",
            prefix="trainer",
            logger_params=logger_params,
            schema_class=TrainerEncounterSchema,
        )
        self.party_cache_service = CacheService(
            alias="TrainerParty",
            prefix="trainer",
            logger_params=logger_params,
            schema_class=TrainerPartyMemberSchema,
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerExplorationRepository(session))

    def _home_key(self, trainer_id: str) -> str:
        return self.home_cache_service.cache.build_key("trainer", "home", trainer_id)

    def _encounter_key(self, trainer_id: str) -> str:
        return self.encounter_cache_service.cache.build_key(
            "trainer",
            "encounters",
            trainer_id,
        )

    def _party_key(self, trainer_id: str) -> str:
        return self.party_cache_service.cache.build_key("trainer", "party", trainer_id)

    async def _invalidate_cache(self, trainer_id: str) -> None:
        await self.home_cache_service.cache.delete_cache(self._home_key(trainer_id))
        await self.encounter_cache_service.cache.delete_cache(
            self._encounter_key(trainer_id)
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
            fresh = await self.repository.find_trainer_encounter(trainer_id, entity.id)
            if fresh is not None:
                result.append(fresh)
        return result

    async def list_encounters(self, current_user: User) -> list[TrainerEncounterSchema]:
        trainer = await self._get_trainer_or_404(current_user)
        key = self._encounter_key(str(trainer.id))
        cached = await self.encounter_cache_service.get_list(key)
        if cached:
            return cached
        entities = await self.repository.list_trainer_encounters(trainer.id)
        serialized = [self.to_encounter_schema(entity) for entity in entities]
        await self.encounter_cache_service.set_list(key, serialized)
        return serialized

    async def select_active_encounter(
        self,
        current_user: User,
        payload: SelectTrainerEncounterSchema,
    ) -> TrainerEncounterSchema:
        trainer = await self._get_trainer_or_404(current_user)
        entity = await self.repository.find_trainer_encounter(trainer.id, payload.encounter_id)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer encounter not found",
            )
        await self.repository.deactivate_all_encounters(trainer.id)
        entity.is_active = True
        await self.repository.session.commit()
        await self._invalidate_cache(str(trainer.id))
        fresh = await self.repository.find_trainer_encounter(trainer.id, payload.encounter_id)
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
                PokedexService.to_schema(entry) for entry in latest_discoveries
            ],
        )
        await self.home_cache_service.set_one(key, serialized)
        return serialized

    @staticmethod
    def to_encounter_schema(entity) -> TrainerEncounterSchema:
        return TrainerEncounterSchema(
            id=entity.id,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            pokemon_encounter=entity.pokemon_encounter,
        )

    @staticmethod
    def to_party_schema(entity) -> TrainerPartyMemberSchema:
        return TrainerPartyMemberSchema(
            id=entity.id,
            slot=entity.slot,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            my_pokemon=TrainerExplorationService.to_my_pokemon_schema(
                entity.my_pokemon
            ),
        )

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
        return MyPokemonSchema(
            id=entity.id,
            name=entity.name,
            nickname=entity.nickname,
            level=entity.level,
            experience=entity.experience,
            hp=entity.hp,
            max_hp=entity.max_hp,
            attack=entity.attack,
            defense=entity.defense,
            special_attack=entity.special_attack,
            special_defense=entity.special_defense,
            speed=entity.speed,
            captured_at=entity.captured_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            pokemon=entity.pokemon,
            trainer=entity.trainer,
            moves=[
                MyPokemonOwnedMoveSchema(
                    id=move.id,
                    pp=move.pp,
                    max_pp=move.max_pp,
                    pokemon_move_id=move.pokemon_move_id,
                    pokemon_move_name=move.pokemon_move.name,
                    pokemon_move_type=move.pokemon_move.type,
                    pokemon_move_power=move.pokemon_move.power,
                    pokemon_move_accuracy=move.pokemon_move.accuracy,
                )
                for move in entity.moves
                if move.deleted_at is None and move.pokemon_move is not None
            ],
        )
