from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.trainer.pokedex.pokedex_entry.schema import PokedexEntrySchema


class PokedexSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entries: list[PokedexEntrySchema] = []
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
