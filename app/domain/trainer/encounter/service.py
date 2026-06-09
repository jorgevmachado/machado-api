from __future__ import annotations

import logging
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.encounter.business import resolve_initial_active_encounter

from app.domain.trainer.encounter.repository import TrainerEncounterRepository
from app.domain.trainer.encounter.schema import (
    TrainerEncounterSchema,
)
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    Encounter,
    TrainerEncounter,
    Trainer,
    TrainerLogEventEnum,
    LogTypeEnum,
    LogStatusEnum,
)
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)


class TrainerEncounterService(
    BaseService[TrainerEncounterRepository, TrainerEncounter]
):
    def __init__(
        self,
        repository: TrainerEncounterRepository,
        trainer_log: TrainerLogService | None = None,
    ) -> None:
        super().__init__(
            alias="TrainerEncounter",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="TrainerEncounterService",
                operation="trainer.encounter",
            ),
            schema_class=TrainerEncounterSchema,
            cache_prefix="trainer_encounter",
        )
        session = repository.session
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerEncounterRepository(session))

    async def sync_from_resources(
        self,
        trainer_id: UUID,
        encounters: list[Encounter],
    ) -> list[TrainerEncounter]:
        sync: list[TrainerEncounter] = []
        active_encounter = resolve_initial_active_encounter(encounters)
        for resource in encounters:
            sync.append(
                await self.get_or_create(
                    trainer_id=trainer_id,
                    encounter=resource,
                    is_active=active_encounter.id == resource.id,
                )
            )
        return sync

    async def get_or_create(
        self, trainer_id: UUID, encounter: Encounter, is_active: bool = False
    ) -> TrainerEncounter:
        entity = await self.repository.find_by(
            trainer_id=trainer_id, pokemon_encounter_id=encounter.id
        )
        if entity:
            return entity

        return await self.repository.save(
            entity=TrainerEncounter(
                is_active=is_active,
                trainer_id=trainer_id,
                pokemon_encounter_id=encounter.id,
            )
        )

    async def get_or_create_list(
        self,
        trainer: Trainer,
        encounters: list[Encounter] | None = None,
    ) -> list[TrainerEncounter]:
        known_encounters = trainer.known_encounters
        if known_encounters and len(known_encounters) > 0:
            return known_encounters

        exist_know_encounters = await self.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id)
        )

        if exist_know_encounters:
            return exist_know_encounters

        if not encounters:
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CREATED,
                user_id=trainer.user.id,
                log_type=LogTypeEnum.ENCOUNTER,
                status=LogStatusEnum.ERROR,
                trainer_id=trainer.id,
                message="Could not load encounters",
            )
            return []

        trainer_encounters = await self.sync_from_resources(
            trainer_id=trainer.id, encounters=encounters
        )

        await self.trainer_log.create(
            event=TrainerLogEventEnum.CREATED,
            user_id=trainer.user.id,
            log_type=LogTypeEnum.ENCOUNTER,
            trainer_id=trainer.id,
            trainer_encounters=trainer_encounters,
        )
        
        return trainer_encounters

    async def update_list(self, trainer: Trainer, encounters: list[Encounter]) -> list[TrainerEncounter]:
        known_encounters = await self.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id)
        )

        known_encounters_map = {
            str(encounter.pokemon_encounter_id): encounter for encounter in known_encounters
        }

        for encounter in encounters:
            known = known_encounters_map.get(str(encounter.id))
            if known:
                continue
            created_encounter = await self.get_or_create(
                trainer_id=trainer.id,
                encounter=encounter,
                is_active=False,
            )
            await self.trainer_log.create(
                event=TrainerLogEventEnum.UPDATED,
                user_id=trainer.user.id,
                log_type=LogTypeEnum.ENCOUNTER,
                trainer_id=trainer.id,
                trainer_encounters=[created_encounter],
            )
        return await self.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id)
        )
    
    async def select_active(self, trainer: Trainer, encounter_id: str) -> TrainerEncounter:        
        entity = await self.repository.find_by(
            trainer_id=trainer.id, pokemon_encounter_id=encounter_id
        )
        if not entity:
            await self.trainer_log.create(
                event=TrainerLogEventEnum.UPDATED,
                user_id=trainer.user.id,
                log_type=LogTypeEnum.ENCOUNTER,
                status=LogStatusEnum.ERROR,
                trainer_id=trainer.id,
                message="Could not load encounters",
            )

            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"{self.alias} not found",
            )
            
            
        trainer_encounters = await self._deactivate_all_encounters(trainer=trainer)
        entity.is_active = True
        entity_updated = await self.repository.update(entity=entity)

        list_trainer_encounters: list[TrainerEncounter] = []
        for trainer_encounter in trainer_encounters:
            trainer_encounter.is_active = trainer_encounter.id == entity_updated.id
            list_trainer_encounters.append(trainer_encounter)

        await self.trainer_log.create(
            event=TrainerLogEventEnum.UPDATED,
            user_id=trainer.user.id,
            log_type=LogTypeEnum.ENCOUNTER,
            trainer_id=trainer.id,
            trainer_encounters=list_trainer_encounters,
        )

        return entity_updated

        
        
    async def _deactivate_all_encounters(self, trainer: Trainer) -> list[TrainerEncounter]:
        list_entity = await self.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id)
        )
        
        trainer_encounters: list[TrainerEncounter] = []

        for entity in list_entity:
            entity.is_active = False
            trainer_encounters.append(await self.repository.update(entity))
        return trainer_encounters