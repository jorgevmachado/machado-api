from __future__ import annotations

from sqlalchemy.orm import selectinload
from app.core.repository.base import BaseRepository
from app.models.pokedex import Pokedex


class PokedexRepository(BaseRepository[Pokedex]):
    model = Pokedex
    relations = (selectinload(Pokedex.entries),)
