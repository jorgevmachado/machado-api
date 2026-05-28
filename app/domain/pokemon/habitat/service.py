from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.habitat.repository import HabitatRepository
from app.domain.pokemon.habitat.schema import (
    HabitatSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Habitat
from app.shared.utils.number import ensure_order_number

logger = logging.getLogger(__name__)


class HabitatService(BaseService[HabitatRepository, Habitat]):
    def __init__(
        self,
        repository: HabitatRepository,
        client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias="Habitat",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="HabitatService", operation="pokemon.habitat"
            ),
            schema_class=HabitatSchema,
            cache_prefix="habitat",
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        client: PokeApiClient | None = None,
    ):
        return cls(HabitatRepository(session), client)

    async def sync_from_resource(self, resource: dict | None) -> Habitat | None:
        if not resource:
            return None

        url = resource.get("url")
        order = ensure_order_number(url)

        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        name = resource.get("name")

        if name is None:
            raise ValueError("Name cannot be None when creating a new PokemonHabitat")
        if url is None:
            raise ValueError("URL cannot be None when creating a new PokemonHabitat")

        return await self.repository.save(
            entity=Habitat(
                url=url,
                name=name,
                order=order,
            )
        )
