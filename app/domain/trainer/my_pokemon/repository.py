from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import CustomLimitOffsetPage, is_paginate
from app.core.pagination.pagination import get_limit_offset_params
from app.core.repository.base import BaseRepository
from app.models import MyPokemon, MyPokemonMove, Pokemon, PokemonMove, PokemonType
from app.shared.schemas import FilterPage


class MyPokemonRepository(BaseRepository[MyPokemon]):
    model = MyPokemon
    default_order_by = "created_at"
    relations = (
        selectinload(MyPokemon.pokemon).selectinload(Pokemon.types),
        selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.weaknesses),
        selectinload(MyPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(PokemonType.strengths),
        selectinload(MyPokemon.trainer),
        selectinload(MyPokemon.moves).selectinload(MyPokemonMove.pokemon_move),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_all(self, page_filter: FilterPage | None = None):
        filter_page = FilterPage.build(page_filter)
        query = (
            select(MyPokemon)
            .where(MyPokemon.deleted_at.is_(None))
        )
        for option in self.relations:
            query = query.options(option)

        trainer_id = getattr(filter_page, "trainer_id", None)
        name = getattr(filter_page, "name", None)
        pokemon_name = getattr(filter_page, "pokemon_name", None)

        if trainer_id:
            query = query.where(MyPokemon.trainer_id == trainer_id)

        if name:
            query = query.where(MyPokemon.name.ilike(f"%{name}%"))
        if pokemon_name:
            query = query.where(MyPokemon.pokemon.has(name=pokemon_name))

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

    async def find_by(self, **kwargs: Any) -> MyPokemon | None:
        query = select(MyPokemon).where(MyPokemon.deleted_at.is_(None))
        for option in self.relations:
            query = query.options(option)

        trainer_id = kwargs.get("trainer_id")
        if trainer_id is not None:
            query = query.where(MyPokemon.trainer_id == trainer_id)

        entity_id = kwargs.get("id")
        if entity_id is not None:
            query = query.where(MyPokemon.id == entity_id)

        name = kwargs.get("name")
        if name is not None:
            query = query.where(MyPokemon.name == name)

        pokemon_name = kwargs.get("pokemon_name")
        if pokemon_name is not None:
            query = query.where(MyPokemon.pokemon.has(name=pokemon_name))

        return await self.session.scalar(query)

    async def find_base_pokemon(self, pokemon_name: str) -> Pokemon | None:
        query = (
            select(Pokemon)
            .where(Pokemon.name == pokemon_name, Pokemon.deleted_at.is_(None))
            .options(selectinload(Pokemon.types), selectinload(Pokemon.moves))
        )
        return await self.session.scalar(query)

    async def list_existing_owned_names(self, trainer_id: UUID) -> set[str]:
        rows = await self.session.scalars(
            select(MyPokemon.name).where(
                MyPokemon.trainer_id == trainer_id,
                MyPokemon.deleted_at.is_(None),
            )
        )
        return set(rows.all())

    async def create_owned(
        self,
        *,
        trainer_id: UUID,
        pokemon_id: UUID,
        name: str,
        nickname: str,
        attributes: dict[str, int],
    ) -> MyPokemon:
        entity = MyPokemon(
            trainer_id=trainer_id,
            pokemon_id=pokemon_id,
            name=name,
            nickname=nickname,
            **attributes,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def attach_moves(
        self,
        *,
        my_pokemon_id: UUID,
        moves: list[PokemonMove],
    ) -> None:
        for move in moves:
            owned_move = MyPokemonMove(
                my_pokemon_id=my_pokemon_id,
                pokemon_move_id=move.id,
                pp=move.pp,
                max_pp=move.pp,
            )
            self.session.add(owned_move)
        await self.session.flush()

    async def soft_delete_owned_move(self, owned_move: MyPokemonMove) -> MyPokemonMove:
        owned_move.deleted_at = owned_move.updated_at
        return await self.update(owned_move)
