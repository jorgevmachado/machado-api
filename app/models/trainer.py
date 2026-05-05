from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import table_registry
from app.models.common import utcnow


@table_registry.mapped_as_dataclass
class Trainer:
    __tablename__ = "trainers"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    pokeballs: Mapped[int] = mapped_column(Integer, nullable=False)
    capture_rate: Mapped[int] = mapped_column(Integer, nullable=False)

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default_factory=uuid4, init=False
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
