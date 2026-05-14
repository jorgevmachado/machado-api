from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.domain.my_pokemon.schema import MyPokemonSchema
from app.domain.pokedex.schema import PokedexSchema


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


class TrainerOnboardingResponseSchema(TrainerSchema):
    my_pokemons: list[MyPokemonSchema] = []
    pokedex: list[PokedexSchema] = []
