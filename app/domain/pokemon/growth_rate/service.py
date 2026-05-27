from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.growth_rate.repository import GrowthRateRepository
from app.domain.pokemon.growth_rate.schema import (
    GrowthRateSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import GrowthRate

logger = logging.getLogger(__name__)


class GrowthRateService(BaseService[GrowthRateRepository, GrowthRate]):
    def __init__(
            self,
            repository: GrowthRateRepository,
            client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias='GrowthRate',
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service='GrowthRateService', operation='pokemon.growth_rate'
            ),
            schema_class=GrowthRateSchema,
            cache_prefix='growth_rate',
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession,client: PokeApiClient | None = None,):
        return cls(GrowthRateRepository(session), client)
