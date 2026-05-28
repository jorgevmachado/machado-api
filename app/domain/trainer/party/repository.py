from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.trainer_party import TrainerParty


class TrainerPartyRepository(BaseRepository[TrainerParty]):
    model = TrainerParty
