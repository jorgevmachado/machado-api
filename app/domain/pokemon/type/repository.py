from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.type import Type


class TypeRepository(BaseRepository[Type]):
    model = Type
