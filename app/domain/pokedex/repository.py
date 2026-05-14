from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CustomLimitOffsetPage, is_paginate
from app.core.pagination.pagination import get_limit_offset_params
from app.core.repository.base import BaseRepository
from app.models import Pokedex, Pokemon, PokemonType
from app.shared.schemas import FilterPage


class PokedexRepository(BaseRepository[Pokedex]):
    model = Pokedex
    default_order_by = "pokemon.order"
    relations = (
        selectinload(Pokedex.pokemon).selectinload(Pokemon.types),
        selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.weaknesses),
        selectinload(Pokedex.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.strengths),
        selectinload(Pokedex.trainer),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_catalog_pokemon(self) -> list[Pokemon]:
        query = (
            select(Pokemon)
            .where(Pokemon.deleted_at.is_(None))
            .options(selectinload(Pokemon.types))
            .order_by(Pokemon.order)
        )
        result = await self.session.scalars(query)
        return result.all()

    async def list_owned(
        self,
        trainer_id: UUID,
        page_filter: FilterPage | None = None,
    ):
        query = (
            select(Pokedex)
            .join(Pokedex.pokemon)
            .where(
                Pokedex.trainer_id == trainer_id,
                Pokedex.deleted_at.is_(None),
                Pokemon.deleted_at.is_(None),
            )
            .order_by(Pokemon.order)
        )
        for option in self.relations:
            query = query.options(option)

        if page_filter is not None:
            filters = page_filter.model_dump(exclude_none=True)
            nickname = filters.get("nickname")
            pokemon_name = filters.get("pokemon_name")
            discovered = filters.get("discovered")

            if nickname:
                query = query.where(Pokedex.nickname.ilike(f"%{nickname}%"))
            if pokemon_name:
                query = query.where(Pokedex.pokemon.has(name=pokemon_name))
            if discovered is not None:
                query = query.where(Pokedex.discovered == discovered)

        if is_paginate(page_filter):
            params = get_limit_offset_params(page_filter)
            result = await paginate(self.session, query, params=params)
            total = getattr(result, "total", None)
            if total is None and hasattr(result, "meta"):
                total = getattr(result.meta, "total", None)
            return CustomLimitOffsetPage.create(
                items=result.items,
                total=total,
                params=params,
            )

        result = await self.session.scalars(query)
        return result.all()

    async def find_owned_detail(
        self,
        trainer_id: UUID,
        pokemon_name: str,
    ) -> Pokedex | None:
        query = (
            select(Pokedex)
            .join(Pokedex.pokemon)
            .where(
                Pokedex.trainer_id == trainer_id,
                Pokedex.deleted_at.is_(None),
                Pokemon.deleted_at.is_(None),
                Pokemon.name == pokemon_name,
            )
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def create_for_trainer(
        self,
        *,
        trainer_id: UUID,
        pokemons: list[Pokemon],
        discovered_pokemon_name: str | None = None,
        discovered_at: datetime | None = None,
        attributes_by_pokemon_id: dict[UUID, dict[str, int]],
    ) -> list[Pokedex]:
        entries: list[Pokedex] = []

        for pokemon in pokemons:
            entry = Pokedex(
                trainer_id=trainer_id,
                pokemon_id=pokemon.id,
                nickname=None,
                discovered=discovered_pokemon_name == pokemon.name,
                discovered_at=(
                    discovered_at if discovered_pokemon_name == pokemon.name else None
                ),
                **attributes_by_pokemon_id[pokemon.id],
            )
            entries.append(entry)

        self.session.add_all(entries)
        await self.session.flush()
        return entries

    async def mark_discovered(
        self,
        entity: Pokedex,
        *,
        discovered_at: datetime,
    ) -> Pokedex:
        entity.discovered = True
        if entity.discovered_at is None:
            entity.discovered_at = discovered_at
        return await self.update(entity)
