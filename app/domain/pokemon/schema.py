from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.pokemon.ability.schema import PokemonAbilitySchema
from app.domain.pokemon.encounter.schema import PokemonEncounterSchema
from app.domain.pokemon.growth_rate.schema import PokemonGrowthRateSchema
from app.domain.pokemon.habitat.schema import PokemonHabitatSchema
from app.domain.pokemon.image.schema import PokemonImageSchema
from app.domain.pokemon.move.schema import PokemonMoveSchema
from app.domain.pokemon.shape.schema import PokemonShapeSchema
from app.domain.pokemon.type.schema import PokemonTypeSchema
from app.models.enums import PokemonStatusEnum


class PokemonEvolutionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hp: int
    name: str
    order: int
    images: PokemonImageSchema | None = None
    speed: int
    height: int
    weight: int
    status: PokemonStatusEnum
    attack: int
    defense: int
    is_baby: bool
    gender_rate: int
    is_mythical: bool
    description: str | None = None
    is_legendary: bool
    capture_rate: int
    hatch_counter: int
    base_happiness: int
    external_image: str
    special_attack: int
    special_defense: int
    base_experience: int
    evolution_chain: str | None = None
    evolves_from_species: str | None = None
    has_gender_differences: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class PokemonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hp: int
    name: str
    order: int
    types: list[PokemonTypeSchema] = []
    moves: list[PokemonMoveSchema] = []
    images: PokemonImageSchema | None = None
    speed: int
    height: int
    weight: int
    shape: PokemonShapeSchema | None = None
    status: PokemonStatusEnum
    attack: int
    defense: int
    is_baby: bool
    habitat: PokemonHabitatSchema | None = None
    abilities: list[PokemonAbilitySchema] = []
    evolutions: list[PokemonEvolutionSchema] = []
    encounters: list[PokemonEncounterSchema] = []
    growth_rate: PokemonGrowthRateSchema | None = None
    gender_rate: int
    is_mythical: bool
    description: str | None = None
    is_legendary: bool
    capture_rate: int
    hatch_counter: int
    base_happiness: int
    external_image: str
    special_attack: int
    special_defense: int
    base_experience: int
    evolution_chain: str | None = None
    evolves_from_species: str | None = None
    has_gender_differences: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @staticmethod
    def _serialize_collection(
        serialized: dict,
        key: str,
        schema: type[BaseModel],
        *,
        use_serialize: bool = False,
    ) -> None:
        values = serialized.get(key)
        if not values:
            return

        serialized[key] = [
            schema.model_validate(value).serialize()
            if use_serialize
            else schema.model_validate(value).model_dump(mode="json")
            for value in values
        ]

    @staticmethod
    def _serialize_nested_value(
        serialized: dict,
        key: str,
        schema: type[BaseModel],
        *,
        use_serialize: bool = False,
    ) -> None:
        value = serialized.get(key)
        if not value:
            return

        validated = schema.model_validate(value)
        serialized[key] = (
            validated.serialize()
            if use_serialize
            else validated.model_dump(mode="json")
        )

    def serialize(self) -> dict:
        serialized = self.model_dump(mode="json")
        self._serialize_collection(
            serialized, "types", PokemonTypeSchema, use_serialize=True
        )
        self._serialize_collection(serialized, "moves", PokemonMoveSchema)
        self._serialize_collection(serialized, "abilities", PokemonAbilitySchema)
        self._serialize_collection(serialized, "encounters", PokemonEncounterSchema)
        self._serialize_collection(serialized, "evolutions", PokemonEvolutionSchema)
        self._serialize_nested_value(
            serialized, "images", PokemonImageSchema, use_serialize=True
        )
        self._serialize_nested_value(serialized, "growth_rate", PokemonGrowthRateSchema)
        self._serialize_nested_value(serialized, "habitat", PokemonHabitatSchema)
        self._serialize_nested_value(serialized, "shape", PokemonShapeSchema)
        return serialized
