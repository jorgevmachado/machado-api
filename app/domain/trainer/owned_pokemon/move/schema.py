from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.pokemon.move.schema import MoveSchema


class OwnedPokemonMoveSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pp: int
    max_pp: int
    pokemon_move: MoveSchema
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @staticmethod
    def _serialize_collection(
        serialized: dict,
        key: str,
        schema: type[BaseModel],
        *,
        use_serialize: bool = False,
    ) -> None:
        values = serialized.get(key)
        if not values:
            return

        serialized[key] = [
            schema.model_validate(value).serialize()
            if use_serialize
            else schema.model_validate(value).model_dump(mode="json")
            for value in values
        ]
