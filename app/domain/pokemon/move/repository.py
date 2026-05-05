from app.core.repository.base import BaseRepository
from app.models import PokemonMove


class PokemonMoveRepository(BaseRepository[PokemonMove]):
    model = PokemonMove
    default_order_by = "order"
