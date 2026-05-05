from app.core.repository.base import BaseRepository
from app.models import PokemonShape


class PokemonShapeRepository(BaseRepository[PokemonShape]):
    model = PokemonShape
    default_order_by = "order"
