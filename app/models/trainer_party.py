from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.my_pokemon import MyPokemon
    from app.models.trainer import Trainer


@table_registry.mapped_as_dataclass
class TrainerParty:
    __tablename__ = "trainer_party"

    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)
    my_pokemon_id: Mapped[UUID] = mapped_column(
        ForeignKey("my_pokemons.id"),
        nullable=False,
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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
        back_populates="party_slots",
    )
    my_pokemon: Mapped["MyPokemon"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="party_slots",
    )
