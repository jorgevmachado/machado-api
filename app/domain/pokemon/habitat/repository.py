from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.habitat import Habitat


class HabitatRepository(BaseRepository[Habitat]):
    model = Habitat
