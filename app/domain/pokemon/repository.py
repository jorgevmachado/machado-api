from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import (
    Pokemon,
    Type,
)


class PokemonRepository(BaseRepository[Pokemon]):
    model = Pokemon
    default_order_by = "order"
    relations = (
        selectinload(Pokemon.types),
        selectinload(Pokemon.types).selectinload(Type.weaknesses),
        selectinload(Pokemon.types).selectinload(Type.strengths),
        selectinload(Pokemon.moves),
        selectinload(Pokemon.abilities),
        selectinload(Pokemon.evolutions),
        selectinload(Pokemon.images),
        selectinload(Pokemon.growth_rate),
        selectinload(Pokemon.habitat),
        selectinload(Pokemon.shape),
        selectinload(Pokemon.encounters),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_by_names(self, names: set[str]) -> list[Pokemon]:
        if not names:
            return []
        query = select(Pokemon).where(Pokemon.name.in_(names))
        result = await self.session.scalars(query)
        list_pokemon: list[Pokemon] = []
        for pokemon in result.all():
            list_pokemon.append(pokemon)
        return list_pokemon
