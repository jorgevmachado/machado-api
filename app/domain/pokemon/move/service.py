from __future__ import annotations

import logging
import httpx
from typing import cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.move.repository import MoveRepository
from app.domain.pokemon.move.schema import (
    MoveSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Move
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class MoveService(BaseService[MoveRepository, Move]):
    def __init__(
        self,
        repository: MoveRepository,
        client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias="Move",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="MoveService", operation="pokemon.move"
            ),
            schema_class=MoveSchema,
            cache_prefix="move",
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        client: PokeApiClient | None = None,
    ):
        return cls(MoveRepository(session), client)

    async def sync_from_resources(self, resources: list[dict]) -> list[Move]:
        synced: list[Move] = []
        for entry in resources:
            resource = entry.get("move") or entry
            move = await self.get_or_create(resource=resource)
            if move is None:
                continue
            synced.append(move)

        return synced

    async def get_or_create(self, resource: dict) -> Move | None:
        url = cast(str, resource.get("url"))
        order = ensure_order_number(url)
        try:
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
                entity=Move(
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
        except httpx.TimeoutException:
            logger.warning(
                "Timeout while syncing Pokemon move. Skipping move.",
                extra={"move_order": order, "move_url": url},
            )
