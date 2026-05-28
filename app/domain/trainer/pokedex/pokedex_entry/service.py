from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.trainer.pokedex.pokedex_entry.repository import PokedexEntryRepository
from app.domain.trainer.pokedex.pokedex_entry.schema import (
    PokedexEntrySchema,
)
from app.domain.trainer.progression import build_initial_attributes
from app.models import PokedexEntry, Pokemon

logger = logging.getLogger(__name__)


class PokedexEntryService(BaseService[PokedexEntryRepository, PokedexEntry]):
    def __init__(
        self,
        repository: PokedexEntryRepository,
    ) -> None:
        super().__init__(
            alias="PokedexEntry",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="PokedexEntryService",
                operation="trainer.pokedex.pokedex_entry",
            ),
            schema_class=PokedexEntrySchema,
            cache_prefix="pokedex_entry",
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(PokedexEntryRepository(session))

    async def sync_from_resources(
        self,
        pokedex_id: UUID,
        resources: list[Pokemon],
        discovered_at: datetime | None = None,
        discovered_pokemon: Pokemon | None = None,
    ) -> list[PokedexEntry]:
        sync: list[PokedexEntry] = []
        for resource in resources:
            sync.append(
                await self.get_or_create(
                    pokedex_id=pokedex_id,
                    pokemon=resource,
                    discovered_at=discovered_at,
                    discovered_pokemon=discovered_pokemon,
                )
            )
        return sync

    async def get_or_create(
        self,
        pokedex_id: UUID,
        pokemon: Pokemon,
        discovered_at: datetime | None = None,
        discovered_pokemon: Pokemon | None = None,
    ) -> PokedexEntry:
        entity = await self.repository.find_by(
            pokedex_id=pokedex_id, pokemon_id=pokemon.id
        )
        if entity:
            return entity
        attributes = build_initial_attributes(pokemon)
        discovered_pokemon_id = discovered_pokemon.id if discovered_pokemon else None
        discovered = discovered_pokemon_id == pokemon.id
        return await self.repository.save(
            entity=PokedexEntry(
                name=pokemon.name,
                pokedex_id=pokedex_id,
                pokemon_id=pokemon.id,
                discovered=discovered,
                discovered_at=discovered_at if discovered else None,
                **attributes,
            )
        )

    async def find_one_cached(
        self,
        param: str,
        **kwargs,
    ) -> PokedexEntry | None:
        cache_key = param
        pokedex_id = kwargs.get("pokedex_id") if kwargs else None
        pokedex_id = cast(str, pokedex_id) if pokedex_id else None
        if pokedex_id:
            cache_key = f"{pokedex_id}:{param}"
        key = self.cache_service.build_key_one(param=cache_key)
        clean_cache = kwargs.get("clean_cache") if kwargs else False

        if clean_cache:
            await self.cache_service.cache.delete_cache(key)
        cached = await self.cache_service.get_one(key)
        if cached:
            return cached
        item = await self.find_one(param, **kwargs)
        await self.cache_service.set_one(key, item)
        return item
