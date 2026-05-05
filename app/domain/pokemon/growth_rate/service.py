from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.growth_rate.repository import PokemonGrowthRateRepository
from app.domain.pokemon.growth_rate.schema import PokemonGrowthRateSchema
from app.infrastructure.external_api import PokeApiClient
from app.models import PokemonGrowthRate
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class PokemonGrowthRateService(
    BaseService[PokemonGrowthRateRepository, PokemonGrowthRate]
):
    def __init__(
        self,
        repository: PokemonGrowthRateRepository,
        client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias="PokemonGrowthRate",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="PokemonGrowthRateService",
                operation="growth_rate",
            ),
            schema_class=PokemonGrowthRateSchema,
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(PokemonGrowthRateRepository(session), client)

    async def sync_from_resource(
        self, resource: dict | None
    ) -> PokemonGrowthRate | None:
        if not resource:
            return None
        url = resource.get("url")
        order = ensure_order_number(url)
        return await self.get_or_create(order=order, url=url)

    async def get_or_create(
        self, order: int, url: str | None = None
    ) -> PokemonGrowthRate:
        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        external_growth_rate = await self.client.get_growth_rate(order)

        if not external_growth_rate:
            raise ValueError(f"External growth rate not found for order {order}")

        description = get_text_language(
            entries=external_growth_rate.descriptions, title="description"
        )

        return await self.repository.save(
            entity=PokemonGrowthRate(
                url=url,
                name=external_growth_rate.name,
                order=order,
                formula=external_growth_rate.formula,
                description=description.text,
            )
        )
