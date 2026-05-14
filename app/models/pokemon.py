from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow
from app.models.enums import PokemonStatusEnum

if TYPE_CHECKING:
    from app.models.my_pokemon import MyPokemon
    from app.models.pokedex import Pokedex
    from app.models.pokemon_ability import PokemonAbility
    from app.models.pokemon_encounter import PokemonEncounter
    from app.models.pokemon_growth_rate import PokemonGrowthRate
    from app.models.pokemon_habitat import PokemonHabitat
    from app.models.pokemon_image import PokemonImage
    from app.models.pokemon_move import PokemonMove
    from app.models.pokemon_shape import PokemonShape
    from app.models.pokemon_type import PokemonType


@table_registry.mapped_as_dataclass
class Pokemon:
    __tablename__ = "pokemons"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    external_image: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PokemonStatusEnum] = mapped_column(
        SAEnum(PokemonStatusEnum, name="pokemonstatusenum"),
        nullable=False,
        default=PokemonStatusEnum.INCOMPLETE,
    )

    hp: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    speed: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    attack: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    defense: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    special_attack: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    special_defense: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    base_experience: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    capture_rate: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    is_baby: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    is_mythical: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False
    )
    is_legendary: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False
    )
    gender_rate: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    hatch_counter: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    base_happiness: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    evolution_chain: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )
    evolves_from_species: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )
    has_gender_differences: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False
    )
    growth_rate_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pokemon_growth_rates.id"), nullable=True, default=None
    )
    habitat_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pokemon_habitats.id"), nullable=True, default=None
    )
    shape_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pokemon_shapes.id"), nullable=True, default=None
    )

    images_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pokemon_images.id"), nullable=True, default=None
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

    growth_rate: Mapped["PokemonGrowthRate | None"] = relationship(
        lazy=default_lazy, init=False
    )
    images: Mapped["PokemonImage | None"] = relationship(
        lazy=default_lazy,
        init=False,
    )
    habitat: Mapped["PokemonHabitat | None"] = relationship(
        lazy=default_lazy, init=False
    )
    shape: Mapped["PokemonShape | None"] = relationship(lazy=default_lazy, init=False)
    types: Mapped[list["PokemonType"]] = relationship(
        secondary="pokemon_type_links",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
    )
    moves: Mapped[list["PokemonMove"]] = relationship(
        secondary="pokemon_move_links",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
    )
    abilities: Mapped[list["PokemonAbility"]] = relationship(
        secondary="pokemon_ability_links",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
    )
    encounters: Mapped[list["PokemonEncounter"]] = relationship(
        secondary="pokemon_encounter_links",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
    )

    evolutions: Mapped[list["Pokemon"]] = relationship(
        lazy=default_lazy,
        secondary="pokemon_evolution_links",
        primaryjoin="Pokemon.id == pokemon_evolution_links.c.pokemon_id",
        secondaryjoin="Pokemon.id == pokemon_evolution_links.c.evolution_id",
        init=False,
        default_factory=list,
    )
    my_pokemons: Mapped[list["MyPokemon"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemon",
    )
    pokedex: Mapped[list["Pokedex"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemon",
    )
