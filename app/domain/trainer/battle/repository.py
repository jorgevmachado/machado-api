from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models import BattleSession


class BattleRepository(BaseRepository[BattleSession]):
    model = BattleSession
