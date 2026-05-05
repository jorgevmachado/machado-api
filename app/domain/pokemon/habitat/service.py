from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.habitat.repository import PokemonHabitatRepository
from app.domain.pokemon.habitat.schema import PokemonHabitatSchema
from app.infrastructure.external_api import PokeApiClient
from app.models import PokemonHabitat
from app.shared.utils.number import ensure_order_number

logger = logging.getLogger(__name__)


class PokemonHabitatService(BaseService[PokemonHabitatRepository, PokemonHabitat]):
    def __init__(
        self, repository: PokemonHabitatRepository, client: PokeApiClient | None = None
    ) -> None:
        super().__init__(
            alias="PokemonHabitat",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokemonHabitatService", operation="habitat"
            ),
            schema_class=PokemonHabitatSchema,
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(PokemonHabitatRepository(session), client)

    async def sync_from_resource(self, resource: dict | None) -> PokemonHabitat | None:
        if not resource:
            return None
        url = resource.get("url")
        name = resource.get("name")
        order = ensure_order_number(url)
        return await self.get_or_create(order=order, name=name, url=url)

    async def get_or_create(
        self, order: int, name: str | None = None, url: str | None = None
    ) -> PokemonHabitat:
        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        if name is None:
            raise ValueError("Name cannot be None when creating a new PokemonHabitat")
        if url is None:
            raise ValueError("URL cannot be None when creating a new PokemonHabitat")

        return await self.repository.save(
            entity=PokemonHabitat(
                url=url,
                name=name,
                order=order,
            )
        )
