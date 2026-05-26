from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.healing_log import HealingLog
    from app.models.trainer import Trainer


@table_registry.mapped_as_dataclass
class PokemonCenterHealing:
    __tablename__ = "pokemon_center_healings"

    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)
    healed_pokemon_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    restored_hp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    restored_pp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default_factory=utcnow, init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )

    trainer: Mapped["Trainer"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="pokemon_center_healings",
    )
    logs: Mapped[list["HealingLog"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemon_center_healing",
    )
