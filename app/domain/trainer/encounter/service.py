from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.encounter.business import resolve_initial_active_encounter

from app.domain.trainer.encounter.repository import TrainerEncounterRepository
from app.domain.trainer.encounter.schema import (
    TrainerEncounterSchema,
)
from app.models import Encounter, TrainerEncounter

logger = logging.getLogger(__name__)


class TrainerEncounterService(
    BaseService[TrainerEncounterRepository, TrainerEncounter]
):
    def __init__(
        self,
        repository: TrainerEncounterRepository,
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
