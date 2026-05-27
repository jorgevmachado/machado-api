from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.image import Image


class ImageRepository(BaseRepository[Image]):
    model = Image
