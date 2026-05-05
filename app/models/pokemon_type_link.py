from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import table_registry


@table_registry.mapped_as_dataclass
class PokemonTypeLink:
    __tablename__ = "pokemon_type_links"

    pokemon_id: Mapped[UUID] = mapped_column(
        ForeignKey("pokemons.id", ondelete="CASCADE"), primary_key=True
    )
    type_id: Mapped[UUID] = mapped_column(
        ForeignKey("pokemon_types.id", ondelete="CASCADE"), primary_key=True
    )
