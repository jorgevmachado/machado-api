from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.encounter import Encounter


class EncounterRepository(BaseRepository[Encounter]):
    model = Encounter
