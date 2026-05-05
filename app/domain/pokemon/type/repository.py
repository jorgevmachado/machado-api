from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import PokemonType


class PokemonTypeRepository(BaseRepository[PokemonType]):
    model = PokemonType
    default_order_by = "order"
    relations = (
        selectinload(PokemonType.weaknesses),
        selectinload(PokemonType.strengths),
    )
