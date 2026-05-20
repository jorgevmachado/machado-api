from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    BattleActionTypeEnum,
    BattleActorEnum,
    BattleLogTypeEnum,
    BattleSessionStatusEnum,
)


class BattleMoveSchema(BaseModel):
    id: str
    pokemon_move_id: str | None = None
    name: str
    type: str
    power: int
    accuracy: int
    pp: int
    max_pp: int


class BattleSideSchema(BaseModel):
    my_pokemon_id: UUID | None = None
    pokemon_id: UUID | None = None
    name: str
    nickname: str | None = None
    level: int
    current_hp: int
    max_hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int
    moves: list[BattleMoveSchema] = []


class BattleSessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trainer_id: UUID
    exploration_event_id: UUID
    trainer_active_my_pokemon_id: UUID | None = None
    wild_pokemon_id: UUID
    wild_pokemon_name: str
    wild_pokemon_level: int
    turn_number: int
    status: BattleSessionStatusEnum
    trainer_side: BattleSideSchema
    wild_side: BattleSideSchema
    party: list[BattleSideSchema] = []
    created_at: datetime
    updated_at: datetime | None = None

class ActiveBattleSummarySchema(BaseModel):
    battle_session_id: UUID
    status: BattleSessionStatusEnum
    turn_number: int
    wild_pokemon_name: str
    wild_pokemon_level: int
    trainer_active_my_pokemon_id: UUID | None = None
    has_active_battle: bool = True


class BattleTurnSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    turn_number: int
    actor: BattleActorEnum
    action_type: BattleActionTypeEnum
    move_name: str | None = None
    payload: dict = {}
    created_at: datetime


class BattleLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    turn_number: int | None = None
    actor: BattleActorEnum | None = None
    log_type: BattleLogTypeEnum
    message: str
    reference: str | None = None
    payload: dict = {}
    created_at: datetime


class UseBattleMoveSchema(BaseModel):
    move_id: UUID


class SwitchBattlePokemonSchema(BaseModel):
    my_pokemon_id: UUID
