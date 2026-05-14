from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.pokemon.type.schema import PokemonTypeSchema


class PokedexPokemonSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    order: int
    external_image: str
    types: list[PokemonTypeSchema] = []


class PokedexTrainerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    pokeballs: int
    capture_rate: int


class PokedexSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nickname: str | None = None
    level: int
    experience: int
    hp: int
    max_hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int
    discovered: bool
    discovered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    pokemon: PokedexPokemonSummarySchema
    trainer: PokedexTrainerSchema
