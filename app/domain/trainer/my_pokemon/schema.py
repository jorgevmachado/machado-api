from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasPath, BaseModel, ConfigDict, Field, field_validator

from app.domain.pokemon.type.schema import PokemonTypeSchema


class MyPokemonBaseSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    order: int
    external_image: str
    types: list[PokemonTypeSchema] = []


class MyPokemonOwnedMoveSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pp: int
    max_pp: int
    pokemon_move_id: UUID
    pokemon_move_name: str = Field(validation_alias=AliasPath("pokemon_move", "name"))
    pokemon_move_type: str = Field(validation_alias=AliasPath("pokemon_move", "type"))
    pokemon_move_power: int = Field(validation_alias=AliasPath("pokemon_move", "power"))
    pokemon_move_accuracy: int = Field(
        validation_alias=AliasPath("pokemon_move", "accuracy")
    )


class MyPokemonTrainerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    pokeballs: int
    capture_rate: int


class MyPokemonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    nickname: str
    level: int
    experience: int
    hp: int
    max_hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int
    captured_at: datetime
    created_at: datetime
    updated_at: datetime | None = None
    pokemon: MyPokemonBaseSummarySchema
    trainer: MyPokemonTrainerSchema
    moves: list[MyPokemonOwnedMoveSchema] = []

    @field_validator("moves", mode="before")
    @classmethod
    def filter_active_moves(cls, value):
        if not isinstance(value, list):
            return value

        return [
            move
            for move in value
            if getattr(move, "deleted_at", None) is None
            and getattr(move, "pokemon_move", None) is not None
        ]


class CreateMyPokemonSchema(BaseModel):
    pokemon_name: str = Field(min_length=1)
    nickname: str | None = None
