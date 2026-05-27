from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.move import Move


class MoveRepository(BaseRepository[Move]):
    model = Move
