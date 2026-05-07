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

    def serialize(self) -> dict:
        serialized = self.model_dump(mode="json")
        if "types" in serialized and serialized["types"]:
            serialized["types"] = [
                PokemonTypeSchema.model_validate(serialized_type).serialize()
                for serialized_type in serialized["types"]
            ]
        if "moves" in serialized and serialized["moves"]:
            serialized["moves"] = [
                PokemonMoveSchema.model_validate(serialized_move).model_dump(
                    mode="json"
                )
                for serialized_move in serialized["moves"]
            ]
        if "abilities" in serialized and serialized["abilities"]:
            serialized["abilities"] = [
                PokemonAbilitySchema.model_validate(serialized_ability).model_dump(
                    mode="json"
                )
                for serialized_ability in serialized["abilities"]
            ]
        if "encounters" in serialized and serialized["encounters"]:
            serialized["encounters"] = [
                PokemonEncounterSchema.model_validate(serialized_encounter).model_dump(
                    mode="json"
                )
                for serialized_encounter in serialized["encounters"]
            ]
        if "images" in serialized and serialized["images"]:
            serialized["images"] = PokemonImageSchema.model_validate(
                serialized["images"]
            ).serialize()
        if "growth_rate" in serialized and serialized["growth_rate"]:
            serialized["growth_rate"] = PokemonGrowthRateSchema.model_validate(
                serialized["growth_rate"]
            ).model_dump(mode="json")
        if "habitat" in serialized and serialized["habitat"]:
            serialized["habitat"] = PokemonHabitatSchema.model_validate(
                serialized["habitat"]
            ).model_dump(mode="json")
        if "shape" in serialized and serialized["shape"]:
            serialized["shape"] = PokemonShapeSchema.model_validate(
                serialized["shape"]
            ).model_dump(mode="json")
        if 'evolutions' in serialized and serialized['evolutions']:
            serialized['evolutions'] = [
                PokemonEvolutionSchema.model_validate(evo).model_dump(mode='json')
                for evo in serialized['evolutions']
            ]
        return serialized
