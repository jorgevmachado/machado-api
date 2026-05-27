from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.ability import Ability


class AbilityRepository(BaseRepository[Ability]):
    model = Ability
