from __future__ import annotations

from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import TrainerEncounter


class TrainerEncounterRepository(BaseRepository[TrainerEncounter]):
    model = TrainerEncounter
    relations = (selectinload(TrainerEncounter.pokemon_encounter),)
