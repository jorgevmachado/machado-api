from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import table_registry
from app.models import LogStatusEnum, TrainerLogEventEnum, LogTypeEnum
from app.models.common import utcnow


@table_registry.mapped_as_dataclass
class TrainerLog:
    __tablename__ = "trainer_logs"    

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default_factory=uuid4, init=False
    )
    type: Mapped[LogTypeEnum] = mapped_column(
        SAEnum(LogTypeEnum, name="logtypeenum"), nullable=False
    ) 
    status: Mapped[LogStatusEnum] = mapped_column(
        SAEnum(LogStatusEnum, name="logstatusenum"), nullable=False
    )
    event: Mapped[TrainerLogEventEnum] = mapped_column(
        SAEnum(TrainerLogEventEnum, name="trainerlogeventenum"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default_factory=dict)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default_factory=utcnow, init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )

    trainer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trainers.id"), nullable=True, default=None
    )
