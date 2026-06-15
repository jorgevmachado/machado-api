from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import BattleLogTypeEnum, BattleActorEnum


class BattleLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor: BattleActorEnum
    battle_session_id: UUID
    message: str
    payload: dict = {}
    log_type: BattleLogTypeEnum    
    created_at: datetime
    reference: str | None = None    
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
