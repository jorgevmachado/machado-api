from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PokemonShapeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    name: str
    order: int
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
