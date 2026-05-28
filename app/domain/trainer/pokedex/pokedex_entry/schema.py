from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.pokemon.schema import PokemonSchema


class PokedexEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hp: int
    level: int
    speed: int
    max_hp: int
    attack: int
    defense: int
    name: str
    pokemon: PokemonSchema
    experience: int
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
