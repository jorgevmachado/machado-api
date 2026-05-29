from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.trainer_log import TrainerLog


class TrainerLogRepository(BaseRepository[TrainerLog]):
    model = TrainerLog
