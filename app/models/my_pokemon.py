from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.my_pokemon_move import MyPokemonMove
    from app.models.pokemon import Pokemon
    from app.models.trainer import Trainer
    from app.models.trainer_party import TrainerParty


@table_registry.mapped_as_dataclass
class MyPokemon:
    __tablename__ = "my_pokemons"

    name: Mapped[str] = mapped_column(String, nullable=False)
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    hp: Mapped[int] = mapped_column(Integer, nullable=False)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    attack: Mapped[int] = mapped_column(Integer, nullable=False)
    defense: Mapped[int] = mapped_column(Integer, nullable=False)
    special_attack: Mapped[int] = mapped_column(Integer, nullable=False)
    special_defense: Mapped[int] = mapped_column(Integer, nullable=False)
    speed: Mapped[int] = mapped_column(Integer, nullable=False)
    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)
    pokemon_id: Mapped[UUID] = mapped_column(ForeignKey("pokemons.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default_factory=utcnow
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
        back_populates="my_pokemons",
    )
    pokemon: Mapped["Pokemon"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="my_pokemons",
    )
    moves: Mapped[list["MyPokemonMove"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="my_pokemon",
    )
    party_slots: Mapped[list["TrainerParty"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="my_pokemon",
    )
