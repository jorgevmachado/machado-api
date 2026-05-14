from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow
from app.models.enums import ExplorationEventTypeEnum

if TYPE_CHECKING:
    from app.models.trainer import Trainer


@table_registry.mapped_as_dataclass
class ExplorationEvent:
    __tablename__ = "exploration_events"

    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)
    event_type: Mapped[ExplorationEventTypeEnum] = mapped_column(
        SAEnum(ExplorationEventTypeEnum, name="explorationeventtypeenum"),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default_factory=uuid4,
        init=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default_factory=utcnow,
        init=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        init=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        init=False,
    )

    trainer: Mapped["Trainer"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="exploration_events",
    )
