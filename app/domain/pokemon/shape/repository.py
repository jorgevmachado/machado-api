from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.shape import Shape


class ShapeRepository(BaseRepository[Shape]):
    model = Shape
