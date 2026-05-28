from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.trainer.owned_pokemon.schema import OwnedPokemonSchema


class TrainerPartySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slot: int
    is_active: bool
    owned_pokemon: OwnedPokemonSchema
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class UpdateTrainerPartySchema(BaseModel):
    owned_pokemon_ids: list[UUID] = Field(default_factory=list, max_length=6)
