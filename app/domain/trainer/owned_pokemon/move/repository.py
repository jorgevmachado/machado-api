from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.owned_pokemon_move import OwnedPokemonMove


class OwnedPokemonMoveRepository(BaseRepository[OwnedPokemonMove]):
    model = OwnedPokemonMove
