from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PokemonMoveSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pp: int
    url: str
    name: str
    type: str
    power: int
    order: int
    target: str
    effect: str
    accuracy: int
    short_effect: str
    damage_class: str
    effect_chance: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
