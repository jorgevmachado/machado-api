from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.my_pokemon import MyPokemon
    from app.models.pokemon_center_healing import PokemonCenterHealing
    from app.models.trainer import Trainer


@table_registry.mapped_as_dataclass
class HealingLog:
    __tablename__ = "healing_logs"

    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)
    pokemon_center_healing_id: Mapped[UUID] = mapped_column(
        ForeignKey("pokemon_center_healings.id"),
        nullable=False,
    )
    my_pokemon_id: Mapped[UUID] = mapped_column(ForeignKey("my_pokemons.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default_factory=dict)

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
        back_populates="healing_logs",
    )
    my_pokemon: Mapped["MyPokemon"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="healing_logs",
    )
    pokemon_center_healing: Mapped["PokemonCenterHealing"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="logs",
    )
