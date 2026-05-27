from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.encounter.repository import EncounterRepository
from app.domain.pokemon.encounter.schema import (
    EncounterSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Encounter

logger = logging.getLogger(__name__)


class EncounterService(BaseService[EncounterRepository, Encounter]):
    def __init__(
            self,
            repository: EncounterRepository,
            client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias='Encounter',
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service='EncounterService', operation='pokemon.encounter'
            ),
            schema_class=EncounterSchema,
            cache_prefix='encounter',
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession,client: PokeApiClient | None = None,):
        return cls(EncounterRepository(session), client)
