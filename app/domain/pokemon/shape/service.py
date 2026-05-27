from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.shape.repository import ShapeRepository
from app.domain.pokemon.shape.schema import (
    ShapeSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Shape

logger = logging.getLogger(__name__)


class ShapeService(BaseService[ShapeRepository, Shape]):
    def __init__(
            self,
            repository: ShapeRepository,
            client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias='Shape',
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service='ShapeService', operation='pokemon.shape'
            ),
            schema_class=ShapeSchema,
            cache_prefix='shape',
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None,):
        return cls(ShapeRepository(session), client)
