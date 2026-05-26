from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasPath, BaseModel, ConfigDict, Field


class PokemonCenterHealingSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trainer_id: UUID
    healed_pokemon_quantity: int
    restored_hp: int
    restored_pp: int
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class LastHealingSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    healed_pokemon_quantity: int
    restored_hp: int
    restored_pp: int
    created_at: datetime


class PokemonCenterHistoryPokemonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    nickname: str
    hp: int
    max_hp: int


class HealingLogHistorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trainer_id: UUID
    pokemon_center_healing_id: UUID
    my_pokemon_id: UUID
    action_type: str
    restored_hp: int = Field(validation_alias=AliasPath("payload", "restored_hp"))
    restored_pp: int = Field(validation_alias=AliasPath("payload", "restored_pp"))
    was_revived: bool = Field(validation_alias=AliasPath("payload", "was_revived"))
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    my_pokemon: PokemonCenterHistoryPokemonSchema


class PokemonCenterHealingResultSchema(BaseModel):
    success: bool
    message: str
    healing_summary: PokemonCenterHealingSummarySchema | None = None
    restored_pokemon: list[HealingLogHistorySchema] = Field(default_factory=list)
