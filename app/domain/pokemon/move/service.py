from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.move.repository import MoveRepository
from app.domain.pokemon.move.schema import (
    MoveSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Move

logger = logging.getLogger(__name__)


class MoveService(BaseService[MoveRepository, Move]):
    def __init__(
            self,
            repository: MoveRepository,
            client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias='Move',
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service='MoveService', operation='pokemon.move'
            ),
            schema_class=MoveSchema,
            cache_prefix='move',
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession,client: PokeApiClient | None = None,):
        return cls(MoveRepository(session), client)
