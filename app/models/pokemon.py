from __future__ import annotations

from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    Boolean,
    Enum as SAEnum,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import table_registry, default_lazy
from app.models import PokemonStatusEnum
from app.models.common import utcnow

if TYPE_CHECKING:
    from app.models.growth_rate import GrowthRate
    from app.models.image import Image
    from app.models.habitat import Habitat
    from app.models.shape import Shape
    from app.models.type import Type
    from app.models.move import Move
    from app.models.ability import Ability
    from app.models.encounter import Encounter
    from app.models.owned_pokemon import OwnedPokemon


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
        ForeignKey("growth_rates.id"), nullable=True, default=None
    )
    habitat_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("habitats.id"), nullable=True, default=None
    )
    shape_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("shapes.id"), nullable=True, default=None
    )

    images_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("images.id"), nullable=True, default=None
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

    growth_rate: Mapped["GrowthRate | None"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="pokemons",
    )
    images: Mapped["Image | None"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="pokemons",
    )
    habitat: Mapped["Habitat | None"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="pokemons",
    )
    shape: Mapped["Shape | None"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="pokemons",
    )
    types: Mapped[list["Type"]] = relationship(
        secondary="pokemon_type_link",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemons",
    )
    moves: Mapped[list["Move"]] = relationship(
        secondary="pokemon_move_link",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemons",
    )
    abilities: Mapped[list["Ability"]] = relationship(
        secondary="pokemon_ability_link",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemons",
    )
    encounters: Mapped[list["Encounter"]] = relationship(
        secondary="pokemon_encounter_link",
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemons",
    )

    evolutions: Mapped[list["Pokemon"]] = relationship(
        lazy=default_lazy,
        secondary="pokemon_evolution_link",
        primaryjoin="Pokemon.id == pokemon_evolution_link.c.pokemon_id",
        secondaryjoin="Pokemon.id == pokemon_evolution_link.c.evolution_id",
        init=False,
        default_factory=list,
    )

    owned_pokemons: Mapped[list["OwnedPokemon"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="pokemon",
    )
