from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.growth_rate import GrowthRate


class GrowthRateRepository(BaseRepository[GrowthRate]):
    model = GrowthRate
