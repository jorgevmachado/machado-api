from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.trainer.my_pokemon.schema import MyPokemonSchema


class TrainerPartyMemberSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slot: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    my_pokemon: MyPokemonSchema


class UpdateTrainerPartySchema(BaseModel):
    my_pokemon_ids: list[UUID] = Field(default_factory=list, max_length=6)
