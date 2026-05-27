from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.type.repository import TypeRepository
from app.domain.pokemon.type.schema import (
    TypeSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Type

logger = logging.getLogger(__name__)


class TypeService(BaseService[TypeRepository, Type]):
    def __init__(
            self,
            repository: TypeRepository,
            client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias='Type',
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service='TypeService', operation='pokemon.type'
            ),
            schema_class=TypeSchema,
            cache_prefix='type',
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(TypeRepository(session), client)
