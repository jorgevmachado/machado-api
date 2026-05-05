from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import table_registry


@table_registry.mapped_as_dataclass
class PokemonTypeStrength:
    __tablename__ = "pokemon_type_strengths"
    pokemon_type_id: Mapped[str] = mapped_column(
        ForeignKey("pokemon_types.id", ondelete="CASCADE"), primary_key=True
    )
    pokemon_type_strength_id: Mapped[str] = mapped_column(
        ForeignKey("pokemon_types.id", ondelete="CASCADE"), primary_key=True
    )
