from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.battle_log import BattleLog


class BattleLogRepository(BaseRepository[BattleLog]):
    model = BattleLog
