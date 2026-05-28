from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GrowthRateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    name: str
    order: int
    formula: str
    description: str
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
