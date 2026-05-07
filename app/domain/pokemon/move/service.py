from __future__ import annotations

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.move.repository import PokemonMoveRepository
from app.domain.pokemon.move.schema import PokemonMoveSchema
from app.infrastructure.external_api import PokeApiClient
from app.models import PokemonMove
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class PokemonMoveService(BaseService[PokemonMoveRepository, PokemonMove]):
    def __init__(
        self, repository: PokemonMoveRepository, client: PokeApiClient | None = None
    ) -> None:
        super().__init__(
            alias="PokemonMove",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokemonMoveService", operation="move"
            ),
            schema_class=PokemonMoveSchema,
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(PokemonMoveRepository(session), client)

    async def sync_from_resources(self, resources: list[dict]) -> list[PokemonMove]:
        synced: list[PokemonMove] = []
        for entry in resources:
            resource = entry.get("move") or entry
            url = resource.get("url")
            order = ensure_order_number(url)
            try:
                synced.append(await self.get_or_create(order=order, url=url))
            except httpx.TimeoutException:
                logger.warning(
                    "Timeout while syncing Pokemon move. Skipping move.",
                    extra={"move_order": order, "move_url": url},
                )
        return synced

    async def get_or_create(self, order: int, url: str | None = None) -> PokemonMove:
        entity = await self.repository.find_by(order=order)
        if entity:
            return entity
        external_move = await self.client.get_move(order)

        if not external_move:
            raise ValueError(f"External move not found for order {order}")

        effect_entry = get_text_language(
            entries=external_move.effect_entries,
            title="effect",
            subtitle="short_effect",
        )
        flavor_text = get_text_language(
            entries=external_move.flavor_text_entries,
            title="flavor_text",
            group="gold-silver",
        )

        return await self.repository.save(
            entity=PokemonMove(
                pp=external_move.pp,
                url=url,
                type=external_move.type.name,
                name=external_move.name,
                order=order,
                power=external_move.power if external_move.power is not None else 0,
                target=external_move.target.name,
                effect=effect_entry.text,
                priority=external_move.priority,
                accuracy=external_move.accuracy
                if external_move.accuracy is not None
                else 0,
                flavor_text=flavor_text.text,
                short_effect=effect_entry.subtext or "",
                damage_class=external_move.damage_class.name,
                effect_chance=external_move.effect_chance,
            )
        )
