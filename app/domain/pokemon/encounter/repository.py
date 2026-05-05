from app.core.repository.base import BaseRepository
from app.models import PokemonEncounter


class PokemonEncounterRepository(BaseRepository[PokemonEncounter]):
    model = PokemonEncounter
    default_order_by = "order"
