from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.trainer import Trainer


class TrainerRepository(BaseRepository[Trainer]):
    model = Trainer
