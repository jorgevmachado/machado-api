from __future__ import annotations

from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models.type import Type


class TypeRepository(BaseRepository[Type]):
    model = Type
    relations = (
        selectinload(Type.strengths),
        selectinload(Type.weaknesses),
    )
