from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PokemonEncounterSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    name: str
    order: int
    chance: int
    method: str
    version: str
    min_level: int
    max_level: int
    condition: str
    max_chance: int
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
