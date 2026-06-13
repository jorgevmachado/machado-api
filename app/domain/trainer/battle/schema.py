from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.trainer.battle.battle_log.schema import BattleLogSchema
from app.models.enums import BattleSessionStatusEnum


class BattleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    logs: list[BattleLogSchema] = []
    status: BattleSessionStatusEnum
    trainer_id: UUID
    turn_number: int
    wild_pokemon_name: str
    wild_pokemon_level: int
    trainer_party_snapshot: list[dict]
    wild_pokemon_snapshot: dict = {}
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @field_validator("trainer_party_snapshot", mode="before")
    @classmethod
    def normalize_trainer_party_snapshot(cls, value):
        if isinstance(value, dict):
            return [value]
        return value
