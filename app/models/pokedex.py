from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.pokemon import Pokemon
    from app.models.trainer import Trainer


@table_registry.mapped_as_dataclass
class Pokedex:
    __tablename__ = "pokedex"

    hp: Mapped[int] = mapped_column(Integer, nullable=False)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    attack: Mapped[int] = mapped_column(Integer, nullable=False)
    defense: Mapped[int] = mapped_column(Integer, nullable=False)
    special_attack: Mapped[int] = mapped_column(Integer, nullable=False)
    special_defense: Mapped[int] = mapped_column(Integer, nullable=False)
    speed: Mapped[int] = mapped_column(Integer, nullable=False)
    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)
    pokemon_id: Mapped[UUID] = mapped_column(ForeignKey("pokemons.id"), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

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
    pokemon: Mapped["Pokemon"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="pokedex",
    )
