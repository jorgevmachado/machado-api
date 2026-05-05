from app.core.repository.base import BaseRepository
from app.models import PokemonGrowthRate


class PokemonGrowthRateRepository(BaseRepository[PokemonGrowthRate]):
    model = PokemonGrowthRate
    default_order_by = "order"
