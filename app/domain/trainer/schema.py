from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.domain.trainer.my_pokemon.schema import MyPokemonSchema
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.domain.pokemon.encounter.schema import PokemonEncounterSchema


class TrainerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    pokeballs: int
    capture_rate: int
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class OnboardingTrainerSchema(BaseModel):
    pokemon_name: str = Field(min_length=1)
    nickname: str | None = None
    pokeballs: int | None = Field(default=None, ge=1)
    capture_rate: int | None = Field(default=None, ge=1, le=255)


class TrainerOnboardingEncounterSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    pokemon_encounter: PokemonEncounterSchema


class TrainerOnboardingResponseSchema(TrainerSchema):
    my_pokemons: list[MyPokemonSchema] = []
    pokedex: list[PokedexSchema] = []
    known_encounters: list[TrainerOnboardingEncounterSchema] = []
