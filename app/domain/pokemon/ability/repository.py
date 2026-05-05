from app.core.repository.base import BaseRepository
from app.models import PokemonAbility


class PokemonAbilityRepository(BaseRepository[PokemonAbility]):
    model = PokemonAbility
    default_order_by = "order"
