from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.ability.repository import AbilityRepository
from app.domain.pokemon.ability.schema import (
    AbilitySchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Ability

logger = logging.getLogger(__name__)


class AbilityService(BaseService[AbilityRepository, Ability]):
    def __init__(
            self,
            repository: AbilityRepository,
            client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias='Ability',
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service='AbilityService', operation='pokemon.ability'
            ),
            schema_class=AbilitySchema,
            cache_prefix='ability',
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None,):
        return cls(AbilityRepository(session), client)
