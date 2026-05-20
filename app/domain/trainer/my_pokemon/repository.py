from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import MyPokemon, MyPokemonMove, Pokemon, PokemonType


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

    async def find_base_pokemon(self, name: str) -> Pokemon | None:
        query = select(Pokemon).where(Pokemon.name == name)
        return await self.session.scalar(query)