from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.my_pokemon import MyPokemon
    from app.models.pokemon_move import PokemonMove


@table_registry.mapped_as_dataclass
class MyPokemonMove:
    __tablename__ = "my_pokemon_moves"

    my_pokemon_id: Mapped[UUID] = mapped_column(
        ForeignKey("my_pokemons.id"), nullable=False
    )
    pokemon_move_id: Mapped[UUID] = mapped_column(
        ForeignKey("pokemon_moves.id"), nullable=False
    )
    pp: Mapped[int] = mapped_column(Integer, nullable=False)
    max_pp: Mapped[int] = mapped_column(Integer, nullable=False)

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

    my_pokemon: Mapped["MyPokemon"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="moves",
    )
    pokemon_move: Mapped["PokemonMove"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="my_pokemon_moves",
    )
