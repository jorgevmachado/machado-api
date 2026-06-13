from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.pokemon.schema import PokemonSchema


class PokedexEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pokemon_id: UUID
    hp: int
    level: int
    speed: int
    max_hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    name: str
    pokemon: PokemonSchema
    discovered: bool
    experience: int
    discovered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
