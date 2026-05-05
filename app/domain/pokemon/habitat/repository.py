from app.core.repository.base import BaseRepository
from app.models import PokemonHabitat


class PokemonHabitatRepository(BaseRepository[PokemonHabitat]):
    model = PokemonHabitat
    default_order_by = "order"
