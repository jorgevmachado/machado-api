from __future__ import annotations

from sqlalchemy import select
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

    async def find_base_pokemon(self, pokemon_name: str) -> Pokemon | None:
        query = select(Pokemon).where(
            Pokemon.name == pokemon_name,
            Pokemon.deleted_at.is_(None),
        )
        return await self.session.scalar(query)
