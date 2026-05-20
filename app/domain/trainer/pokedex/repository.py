from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import Pokedex, Pokemon, PokemonType


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
