from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow
from app.models.enums import BattleActionTypeEnum, BattleActorEnum

if TYPE_CHECKING:
    from app.models.battle_session import BattleSession


@table_registry.mapped_as_dataclass
class BattleTurn:
    __tablename__ = "battle_turns"

    battle_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("battle_sessions.id"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[BattleActorEnum] = mapped_column(
        SAEnum(BattleActorEnum, name="battleactorenum"),
        nullable=False,
    )
    action_type: Mapped[BattleActionTypeEnum] = mapped_column(
        SAEnum(BattleActionTypeEnum, name="battleactiontypeenum"),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default_factory=dict)
    move_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

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

    battle_session: Mapped["BattleSession"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="turns",
    )
