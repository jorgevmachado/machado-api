from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.ability.repository import PokemonAbilityRepository
from app.domain.pokemon.ability.schema import PokemonAbilitySchema
from app.infrastructure.external_api import PokeApiClient
from app.models import PokemonAbility
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class PokemonAbilityService(BaseService[PokemonAbilityRepository, PokemonAbility]):
    def __init__(
        self, repository: PokemonAbilityRepository, client: PokeApiClient | None = None
    ) -> None:
        super().__init__(
            alias="PokemonAbility",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokemonAbilityService", operation="ability"
            ),
            schema_class=PokemonAbilitySchema,
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(PokemonAbilityRepository(session), client)

    async def sync_from_resources(self, resources: list[dict]) -> list[PokemonAbility]:
        synced: list[PokemonAbility] = []
        for entry in resources:
            resource = entry.get("ability") or entry
            url = resource.get("url")
            slot = resource.get("slot", 0)
            is_hidden = resource.get("is_hidden", False)
            order = ensure_order_number(url)
            synced.append(
                await self.get_or_create(
                    slot=slot, order=order, is_hidden=is_hidden, url=url
                )
            )
        return synced

    async def get_or_create(
        self, order: int, url: str | None = None, is_hidden: bool = False, slot: int = 0
    ) -> PokemonAbility:
        entity = await self.repository.find_by(order=order)
        if entity:
            return entity
        external_ability = await self.client.get_ability(order)

        if not external_ability:
            raise ValueError(f"External ability not found for order {order}")

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
            entity=PokemonAbility(
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
