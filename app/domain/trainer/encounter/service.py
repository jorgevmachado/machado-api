from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.trainer.encounter.business import (
    build_pokeball_reward,
    choose_event_type,
    choose_wild_pokemon,
    resolve_initial_active_encounter,
)
from app.domain.trainer.encounter.repository import TrainerEncounterRepository
from app.domain.trainer.encounter.schema import (
    ExplorationEventSchema,
    SelectTrainerEncounterSchema,
    TrainerEncounterSchema,
)
from app.domain.trainer.battle.repository import BattleSessionRepository
from app.domain.trainer.battle.service import BattleSessionService
from app.models import ExplorationEventTypeEnum, Trainer, TrainerEncounter, User, PokemonEncounter
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class TrainerEncounterService(
    BaseService[TrainerEncounterRepository, TrainerEncounter, TrainerEncounterSchema]
):
    def __init__(
        self,
        repository: TrainerEncounterRepository,
        trainer_service: TrainerService | None = None,
        battle_session_service: BattleSessionService | None = None,
    ) -> None:
        super().__init__(
            alias="TrainerEncounters",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="TrainerExplorationService",
                operation="encounter",
            ),
            schema_class=TrainerEncounterSchema,
            cache_prefix="trainer",
        )
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        self.battle_session_service = (
            battle_session_service
            or BattleSessionService(BattleSessionRepository(session))
        )
        self.encounter_cache_service = self.cache_service

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerEncounterRepository(session))

    async def _invalidate_cache(self, trainer_id: str) -> None:
        await self.encounter_cache_service.cache.delete_cache(
            self.encounter_cache_service.build_key_list(
                FilterPage.build(trainer_id=trainer_id)
            )
        )

    async def _get_trainer_or_404(self, current_user: User) -> Trainer:
        trainer = await self.trainer_service.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer not found",
            )
        return trainer

    async def add_encounters(self, trainer_id: str, pokemon_encounters: list[PokemonEncounter]) -> list[TrainerEncounter]:
        trainer_encounters: list[TrainerEncounter] = []
        for pokemon_encounter in pokemon_encounters:
            trainer_encounter = await self.repository.find_by(trainer_id=trainer_id, pokemon_encounter_id=pokemon_encounter.id)
            if trainer_encounter:
                trainer_encounters.append(trainer_encounter)
                continue
            new_trainer_encounter = await self.repository.save(
                entity=TrainerEncounter(
                    trainer_id=trainer_id,
                    is_active=False,
                    pokemon_encounter_id=pokemon_encounter.id,
                )
            )
            print('# => new_trainer_encounter => id => ', new_trainer_encounter.id)
            trainer_encounters.append(new_trainer_encounter)
        return trainer_encounters

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
            await self.trainer_service.invalidate_home_cache(str(trainer_id))
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
        await self.trainer_service.invalidate_home_cache(str(trainer.id))
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

    async def walk(self, current_user: User) -> ExplorationEventSchema:
        trainer = await self._get_trainer_or_404(current_user)
        if await self.battle_session_service.has_active_battle(trainer.id):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Trainer already has an active battle",
            )
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
        battle_session = None
        if event_type == ExplorationEventTypeEnum.WILD_POKEMON:
            battle_session = (
                await self.battle_session_service.create_or_resume_battle(
                    trainer=trainer,
                    exploration_event=entity,
                    wild_pokemon=pokemon,
                )
            )
            payload["battle_session_id"] = str(battle_session.id)
            payload["battle_status"] = getattr(
                battle_session.status,
                "value",
                battle_session.status,
            )
            payload["has_active_battle"] = True
            entity.payload = payload
        await self.repository.session.commit()
        await self._invalidate_cache(str(trainer.id))
        await self.trainer_service.invalidate_home_cache(str(trainer.id))
        return self.to_event_schema(
            entity,
            active_encounter=active_encounter,
            battle_session=battle_session,
        )

    async def get_active_encounter_by_trainer_id(
        self,
        trainer_id: UUID,
    ) -> TrainerEncounterSchema | None:
        entity = await self.repository.find_active_trainer_encounter(trainer_id)
        if entity is None:
            return None
        return self.to_encounter_schema(entity)

    @staticmethod
    def to_encounter_schema(entity) -> TrainerEncounterSchema:
        return TrainerEncounterSchema.model_validate(entity)

    @staticmethod
    def to_event_schema(
        entity,
        active_encounter=None,
        battle_session=None,
    ) -> ExplorationEventSchema:
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
            battle_session_id=payload.get("battle_session_id"),
            battle_status=(
                battle_session.status
                if battle_session is not None
                else payload.get("battle_status")
            ),
            has_active_battle=payload.get("has_active_battle", False),
        )
