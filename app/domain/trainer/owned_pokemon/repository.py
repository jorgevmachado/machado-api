from __future__ import annotations

from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import Pokemon, Type, OwnedPokemonMove, OwnedPokemon


class OwnedPokemonRepository(BaseRepository[OwnedPokemon]):
    model = OwnedPokemon
    relations = (
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.types),
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.evolutions),
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.abilities),
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.encounters),
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.images),
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.shape),
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.growth_rate),
        selectinload(OwnedPokemon.pokemon).selectinload(Pokemon.habitat),
        selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(Type.weaknesses),
        selectinload(OwnedPokemon.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(Type.strengths),
        selectinload(OwnedPokemon.trainer),
        selectinload(OwnedPokemon.moves).selectinload(OwnedPokemonMove.pokemon_move),
    )
