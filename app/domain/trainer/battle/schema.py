from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.trainer.battle.battle_log.schema import BattleLogSchema
from app.domain.trainer.progression import AttributesCalculatedSchema
from app.models.enums import BattleSessionStatusEnum


class BattleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    logs: list[BattleLogSchema] = []
    status: BattleSessionStatusEnum
    trainer_id: UUID
    turn_number: int
    trainer_party_snapshot: dict = {}
    wild_pokemon_snapshot: dict = {}
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class BattleProcessedSchema(BaseModel):
    error: bool
    status: BattleSessionStatusEnum
    wild_pokemon_damage: int
    wild_pokemon_missed: bool
    owned_pokemon_damage: int
    owned_pokemon_missed: bool
    wild_pokemon_fainted: bool
    owned_pokemon_fainted: bool
    owned_pokemon_move_name: str
    wild_pokemon_progression: AttributesCalculatedSchema
    owned_pokemon_progression: AttributesCalculatedSchema
    error_message: str | None = None
    wild_pokemon_move_name: str | None = None


class OpponentDamageSchema(BaseModel):
    damage: int
    missed: bool
    current_hp: int
