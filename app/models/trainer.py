from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.owned_pokemon import OwnedPokemon
    from app.models.pokedex import Pokedex
    from app.models.trainer_encounter import TrainerEncounter
    from app.models.trainer_party import TrainerParty


@table_registry.mapped_as_dataclass
class Trainer:
    __tablename__ = "trainers"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    pokeballs: Mapped[int] = mapped_column(Integer, nullable=False)
    capture_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    base_capture_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    capture_progress_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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

    owned_pokemons: Mapped[list["OwnedPokemon"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="trainer",
    )
    pokedex: Mapped[list["Pokedex"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="trainer",
    )
    known_encounters: Mapped[list["TrainerEncounter"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="trainer",
    )
    party_slots: Mapped[list["TrainerParty"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="trainer",
    )

    user: Mapped['User'] = relationship(
        init=False,
        lazy=default_lazy,
        back_populates='trainer',
    )
