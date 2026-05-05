from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.shape.repository import PokemonShapeRepository
from app.domain.pokemon.shape.schema import PokemonShapeSchema
from app.infrastructure.external_api import PokeApiClient
from app.models import PokemonShape
from app.shared.utils.number import ensure_order_number

logger = logging.getLogger(__name__)


class PokemonShapeService(BaseService[PokemonShapeRepository, PokemonShape]):
    def __init__(
        self, repository: PokemonShapeRepository, client: PokeApiClient | None = None
    ) -> None:
        super().__init__(
            alias="PokemonShape",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokemonShapeService", operation="shape"
            ),
            schema_class=PokemonShapeSchema,
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(PokemonShapeRepository(session), client)

    async def sync_from_resource(self, resource: dict | None) -> PokemonShape | None:
        if not resource:
            return None
        url = resource.get("url")
        name = resource.get("name")
        order = ensure_order_number(url)
        return await self.get_or_create(name=name, order=order, url=url)

    async def get_or_create(
        self, order: int, name: str | None = None, url: str | None = None
    ) -> PokemonShape:
        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        if name is None:
            raise ValueError("Name cannot be None when creating a new PokemonShape")
        if url is None:
            raise ValueError("URL cannot be None when creating a new PokemonShape")

        return await self.repository.save(
            entity=PokemonShape(
                url=url,
                name=name,
                order=order,
            )
        )
