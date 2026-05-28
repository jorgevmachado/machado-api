from __future__ import annotations

from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import Pokemon, PokedexEntry, Type


class PokedexEntryRepository(BaseRepository[PokedexEntry]):
    model = PokedexEntry
    relations = (
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.types),
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.evolutions),
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.abilities),
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.encounters),
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.images),
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.shape),
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.growth_rate),
        selectinload(PokedexEntry.pokemon).selectinload(Pokemon.habitat),
        selectinload(PokedexEntry.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(Type.weaknesses),
        selectinload(PokedexEntry.pokemon)
        .selectinload(Pokemon.types)
        .selectinload(Type.strengths),
    )
