from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import table_registry
from app.models.common import utcnow


@table_registry.mapped_as_dataclass
class PokemonImage:
    __tablename__ = "pokemon_images"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default_factory=uuid4, init=False
    )
    order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    images: Mapped[str] = mapped_column(Text, nullable=False)
    back_image: Mapped[str] = mapped_column(String, nullable=False)
    front_image: Mapped[str] = mapped_column(String, nullable=False)
    back_source: Mapped[str] = mapped_column(
        String, nullable=False, default="back_default"
    )
    front_source: Mapped[str] = mapped_column(
        String, nullable=False, default="front_default"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default_factory=utcnow, init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
