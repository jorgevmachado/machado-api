from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import table_registry, default_lazy
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.trainer import Trainer
    from app.models.pokedex_entry import PokedexEntry


@table_registry.mapped_as_dataclass
class Pokedex:
    __tablename__ = "pokedex"

    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)

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

    trainer: Mapped["Trainer"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="pokedex",
    )

    entries: Mapped[list["PokedexEntry"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokedex",
    )
