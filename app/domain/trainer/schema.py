from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.trainer.battle.schema import BattleSchema
from app.domain.trainer.encounter.schema import TrainerEncounterSchema
from app.domain.trainer.exploration.schema import ExplorationSchema
from app.domain.trainer.owned_pokemon.schema import OwnedPokemonSchema
from app.domain.trainer.party.schema import TrainerPartySchema
from app.domain.trainer.pokedex.schema import PokedexSchema


class UserTrainerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    username: str


class TrainerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user: UserTrainerSchema
    pokedex: PokedexSchema | None = None
    pokeballs: int
    capture_rate: int
    party_slots: list[TrainerPartySchema] = []
    owned_pokemons: list[OwnedPokemonSchema] = []
    battle_sessions: list[BattleSchema] = []
    known_encounters: list[TrainerEncounterSchema] = []
    base_capture_rate: int
    exploration_events: list[ExplorationSchema]
    capture_progress_points: int
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


class OnboardPayloadSchema(BaseModel):
    pokemon_name: str = Field(min_length=1)
    nickname: str | None = None
    pokeballs: int | None = Field(default=None, ge=1)
    capture_rate: int | None = Field(default=None, ge=1, le=255)


class CapturePayloadSchema(BaseModel):
    nickname: str | None = None
    pokemon_name: str = Field(min_length=1)
