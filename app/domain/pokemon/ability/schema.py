from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AbilitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    name: str
    slot: int
    order: int
    effect: str
    is_hidden: bool
    flavor_text: str
    short_effect: str
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
