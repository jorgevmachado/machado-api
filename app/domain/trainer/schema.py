from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserTrainerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    username: str


class TrainerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user: UserTrainerSchema
    pokeballs: int
    capture_rate: int
    base_capture_rate: int
    capture_progress_points: int
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class OnboardPayloadSchema(BaseModel):
    pokemon_name: str = Field(min_length=1)
    nickname: str | None = None
    pokeballs: int | None = Field(default=None, ge=1)
    capture_rate: int | None = Field(default=None, ge=1, le=255)
