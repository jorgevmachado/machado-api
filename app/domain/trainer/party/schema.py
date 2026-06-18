from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.trainer.owned_pokemon.schema import OwnedPokemonSchema
from app.models import TrainerParty, OwnedPokemonMove


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


class TrainerPartyBattleSchema(BaseModel):
    trainer_party: TrainerParty
    trainer_party_selected_move: OwnedPokemonMove
