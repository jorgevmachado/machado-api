from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.pokemon.schema import PokemonSchema
from app.domain.trainer.owned_pokemon.move.schema import OwnedPokemonMoveSchema


class OwnedPokemonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hp: int
    name: str
    moves: list[OwnedPokemonMoveSchema] = []
    level: int
    speed: int
    max_hp: int
    attack: int
    defense: int
    pokemon: PokemonSchema
    nickname: str
    experience: int
    captured_at: datetime
    special_attack: int
    special_defense: int
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
