from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository.base import BaseRepository
from app.models import MyPokemonMove


class MyPokemonMoveRepository(BaseRepository[MyPokemonMove]):
    model = MyPokemonMove
    default_order_by = "created_at"

    def __init__(self, session: AsyncSession):
        super().__init__(session)
