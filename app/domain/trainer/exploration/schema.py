from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.trainer.battle.schema import BattleSchema
from app.models import ExplorationEventTypeEnum


class ExplorationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payload: dict = {}
    event_type: ExplorationEventTypeEnum
    battle_sessions: list[BattleSchema]
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
