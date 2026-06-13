from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models import ExplorationEvent


class ExplorationRepository(BaseRepository[ExplorationEvent]):
    model = ExplorationEvent
