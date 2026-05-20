from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MyPokemonMoveSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pp: int
    max_pp: int
    my_pokemon_id: UUID
    pokemon_move_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
