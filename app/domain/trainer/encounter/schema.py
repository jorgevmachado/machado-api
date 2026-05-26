from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.trainer.my_pokemon.schema import MyPokemonSchema
from app.domain.trainer.pokemon_center.schema import LastHealingSummarySchema
from app.domain.trainer.pokedex.schema import PokedexPokemonSummarySchema, PokedexSchema
from app.domain.pokemon.encounter.schema import PokemonEncounterSchema
from app.domain.trainer.schema import TrainerSchema
from app.models import ExplorationEventTypeEnum
from app.models.enums import BattleSessionStatusEnum
from app.domain.trainer.battle.schema import ActiveBattleSummarySchema


class TrainerEncounterSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    pokemon_encounter: PokemonEncounterSchema


class SelectTrainerEncounterSchema(BaseModel):
    encounter_id: UUID


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


class ExplorationEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: ExplorationEventTypeEnum
    created_at: datetime
    pokemon: PokedexPokemonSummarySchema | None = None
    encounter: PokemonEncounterSchema | None = None
    pokeballs_found: int | None = None
    trainer_pokeballs: int | None = None
    battle_session_id: UUID | None = None
    battle_status: BattleSessionStatusEnum | None = None
    has_active_battle: bool = False


class TrainerHomeSchema(BaseModel):
    trainer: TrainerSchema
    party: list[TrainerPartyMemberSchema] = Field(default_factory=list)
    encounters: list[TrainerEncounterSchema] = Field(default_factory=list)
    active_encounter: TrainerEncounterSchema | None = None
    latest_discoveries: list[PokedexSchema] = Field(default_factory=list)
    active_battle: ActiveBattleSummarySchema | None = None
    last_healing: LastHealingSummarySchema | None = None
