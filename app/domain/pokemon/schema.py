from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.pokemon.ability.schema import AbilitySchema
from app.domain.pokemon.encounter.schema import EncounterSchema
from app.domain.pokemon.growth_rate.schema import GrowthRateSchema
from app.domain.pokemon.habitat.schema import HabitatSchema
from app.domain.pokemon.image.schema import ImageSchema
from app.domain.pokemon.move.schema import MoveSchema
from app.domain.pokemon.shape.schema import ShapeSchema
from app.domain.pokemon.type.schema import TypeSchema
from app.models import PokemonStatusEnum


class PokemonEvolutionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hp: int
    name: str
    order: int
    speed: int
    height: int
    weight: int
    images: ImageSchema | None = None
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


class PokemonSchema(PokemonEvolutionSchema):
    model_config = ConfigDict(from_attributes=True)

    types: list[TypeSchema] = []
    moves: list[MoveSchema] = []
    shape: ShapeSchema | None = None
    habitat: HabitatSchema | None = None
    abilities: list[AbilitySchema] = []
    evolutions: list[PokemonEvolutionSchema] = []
    encounters: list[EncounterSchema] = []
    growth_rate: GrowthRateSchema | None = None

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
