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
from app.shared.utils.number import ensure_order_number

logger = logging.getLogger(__name__)


class ShapeService(BaseService[ShapeRepository, Shape]):
    def __init__(
        self,
        repository: ShapeRepository,
        client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias="Shape",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="ShapeService", operation="pokemon.shape"
            ),
            schema_class=ShapeSchema,
            cache_prefix="shape",
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        client: PokeApiClient | None = None,
    ):
        return cls(ShapeRepository(session), client)

    async def sync_from_resource(self, resource: dict | None) -> Shape | None:
        if not resource:
            return None

        url = resource.get("url")
        order = ensure_order_number(url)

        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        name = resource.get("name")

        if name is None:
            raise ValueError("Name cannot be None when creating a new Shape")
        if url is None:
            raise ValueError("URL cannot be None when creating a new Shape")

        return await self.repository.save(
            entity=Shape(
                url=url,
                name=name,
                order=order,
            )
        )
