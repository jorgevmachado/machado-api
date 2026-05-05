from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models import PokemonStatusEnum
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.pokemon import Pokemon


@table_registry.mapped_as_dataclass
class PokemonType:
    __tablename__ = "pokemon_types"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default_factory=uuid4, init=False
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    badge_url: Mapped[str] = mapped_column(String, nullable=False)
    badge_icon_url: Mapped[str] = mapped_column(String, nullable=False)
    badge_shield_url: Mapped[str] = mapped_column(String, nullable=False)
    badge_legends_url: Mapped[str] = mapped_column(String, nullable=False)
    badge_legend_icon_url: Mapped[str] = mapped_column(String, nullable=False)
    badge_shield_icon_url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PokemonStatusEnum] = mapped_column(
        SAEnum(PokemonStatusEnum, name="pokemonstatusenum"),
        nullable=False,
        default=PokemonStatusEnum.INCOMPLETE,
    )
    text_color: Mapped[str] = mapped_column(String, nullable=False, default="#111827")
    background_color: Mapped[str] = mapped_column(
        String, nullable=False, default="#E5E7EB"
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

    pokemons: Mapped[list["Pokemon"]] = relationship(
        secondary="pokemon_type_links",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
    )

    weaknesses: Mapped[list["PokemonType"]] = relationship(
        lazy=default_lazy,
        init=False,
        secondary="pokemon_type_weaknesses",
        primaryjoin="PokemonType.id == pokemon_type_weaknesses.c.pokemon_type_id",
        secondaryjoin="PokemonType.id == pokemon_type_weaknesses.c.pokemon_type_weakness_id",
    )

    strengths: Mapped[list["PokemonType"]] = relationship(
        lazy=default_lazy,
        init=False,
        secondary="pokemon_type_strengths",
        primaryjoin="PokemonType.id == pokemon_type_strengths.c.pokemon_type_id",
        secondaryjoin="PokemonType.id == pokemon_type_strengths.c.pokemon_type_strength_id",
    )
