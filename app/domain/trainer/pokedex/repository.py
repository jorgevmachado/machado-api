from __future__ import annotations

from datetime import datetime
from typing import Any
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
        selectinload(Pokedex.pokemon).selectinload(Pokemon.types).selectinload(PokemonType.weaknesses),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.types).selectinload(PokemonType.strengths),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.moves),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.images),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.shape),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.habitat),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.abilities),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.evolutions),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.encounters),
        selectinload(Pokedex.pokemon).selectinload(Pokemon.growth_rate),
        selectinload(Pokedex.trainer),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_all(self, page_filter: FilterPage | None = None):
        filter_page = FilterPage.build(page_filter)
        query = (
            select(Pokedex)
            .join(Pokedex.pokemon)
            .where(
                Pokedex.deleted_at.is_(None),
                Pokemon.deleted_at.is_(None),
            )
        )
        for option in self.relations:
            query = query.options(option)

        trainer_id = getattr(filter_page, "trainer_id", None)
        nickname = getattr(filter_page, "nickname", None)
        pokemon_name = getattr(filter_page, "pokemon_name", None)
        discovered = getattr(filter_page, "discovered", None)

        if trainer_id:
            query = query.where(Pokedex.trainer_id == trainer_id)
        if nickname:
            query = query.where(Pokedex.nickname.ilike(f"%{nickname}%"))
        if pokemon_name:
            query = query.where(Pokemon.name == pokemon_name)
        if discovered is not None:
            query = query.where(Pokedex.discovered == discovered)

        query = self._apply_order_by(query, filter_page)

        if is_paginate(filter_page):
            params = get_limit_offset_params(filter_page)
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

    async def find_by(self, **kwargs: Any) -> Pokedex | None:
        query = (
            select(Pokedex)
            .join(Pokedex.pokemon)
            .where(
                Pokedex.deleted_at.is_(None),
                Pokemon.deleted_at.is_(None),
            )
        )
        for option in self.relations:
            query = query.options(option)

        trainer_id = kwargs.get("trainer_id")
        if trainer_id is not None:
            query = query.where(Pokedex.trainer_id == trainer_id)

        entity_id = kwargs.get("id")
        if entity_id is not None:
            query = query.where(Pokedex.id == entity_id)

        name = kwargs.get("name")
        if name is not None:
            query = query.where(Pokemon.name == name)

        pokemon_name = kwargs.get("pokemon_name")
        if pokemon_name is not None:
            query = query.where(Pokemon.name == pokemon_name)

        discovered = kwargs.get("discovered")
        if discovered is not None:
            query = query.where(Pokedex.discovered == discovered)

        return await self.session.scalar(query)

    async def list_catalog_pokemon(self) -> list[Pokemon]:
        query = (
            select(Pokemon)
            .where(Pokemon.deleted_at.is_(None))
            .options(selectinload(Pokemon.types))
            .order_by(Pokemon.order)
        )
        result = await self.session.scalars(query)
        return result.all()

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
