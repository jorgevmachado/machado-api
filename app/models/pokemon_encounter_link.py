from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import table_registry


@table_registry.mapped_as_dataclass
class PokemonEncounterLink:
    __tablename__ = "pokemon_encounter_links"

    pokemon_id: Mapped[UUID] = mapped_column(
        ForeignKey("pokemons.id", ondelete="CASCADE"), primary_key=True
    )
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("pokemon_encounters.id", ondelete="CASCADE"), primary_key=True
    )
