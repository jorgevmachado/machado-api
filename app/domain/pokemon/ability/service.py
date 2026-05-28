from __future__ import annotations

import logging
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.pokemon.ability.repository import AbilityRepository
from app.domain.pokemon.ability.schema import (
    AbilitySchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.models import Ability
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class AbilityService(BaseService[AbilityRepository, Ability]):
    def __init__(
        self,
        repository: AbilityRepository,
        client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias="Ability",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="AbilityService", operation="pokemon.ability"
            ),
            schema_class=AbilitySchema,
            cache_prefix="ability",
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        client: PokeApiClient | None = None,
    ):
        return cls(AbilityRepository(session), client)

    async def sync_from_resources(self, resources: list[dict]) -> list[Ability]:
        synced: list[Ability] = []
        for entry in resources:
            resource = entry.get("ability") or entry
            ability = await self.get_or_create(resource=resource)
            if ability is None:
                continue
            synced.append(ability)

        return synced

    async def get_or_create(self, resource: dict) -> Ability | None:
        url = cast(str, resource.get("url"))
        order = ensure_order_number(url)
        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        external_ability = await self.client.get_ability(order)

        if not external_ability:
            raise ValueError(f"External ability not found for order {order}")

        slot = resource.get("slot", 0)
        is_hidden = resource.get("is_hidden", False)

        effect_entry = get_text_language(
            entries=external_ability.effect_entries,
            title="effect",
            subtitle="short_effect",
        )
        flavor_text = get_text_language(
            entries=external_ability.flavor_text_entries,
            title="flavor_text",
            group="ruby-sapphire",
        )

        return await self.repository.save(
            entity=Ability(
                url=url,
                name=external_ability.name,
                order=order,
                slot=slot,
                effect=effect_entry.text,
                is_hidden=is_hidden,
                flavor_text=flavor_text.text,
                short_effect=effect_entry.subtext or "",
            )
        )
