from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel

from app.domain.pokemon.image.schema import ImageSchema
from app.domain.pokemon.schema import PokemonSchema
from app.models import PokemonStatusEnum


class _SerializableSchema(BaseModel):
    value: str

    def serialize(self) -> dict[str, str]:
        return {"serialized": self.value}


class TestPokemonSchema:
    @staticmethod
    def test_serialize_collection_handles_empty_values() -> None:
        serialized = {"types": []}

        PokemonSchema._serialize_collection(serialized, "types", ImageSchema)

        assert serialized["types"] == []

    @staticmethod
    def test_serialize_collection_uses_model_dump_by_default() -> None:
        now = datetime.now(timezone.utc)
        serialized = {
            "images": [
                {
                    "id": uuid4(),
                    "order": 1,
                    "images": ["a"],
                    "back_image": "back",
                    "front_image": "front",
                    "back_source": "back_default",
                    "front_source": "front_default",
                    "created_at": now,
                    "updated_at": None,
                    "deleted_at": None,
                }
            ]
        }

        PokemonSchema._serialize_collection(serialized, "images", ImageSchema)

        assert serialized["images"][0]["order"] == 1

    @staticmethod
    def test_serialize_collection_uses_custom_serialize_when_requested() -> None:
        serialized = {"values": [{"value": "ok"}]}

        PokemonSchema._serialize_collection(
            serialized,
            "values",
            _SerializableSchema,
            use_serialize=True,
        )

        assert serialized["values"] == [{"serialized": "ok"}]

    @staticmethod
    def test_pokemon_schema_model_validate_supports_nested_relations() -> None:
        now = datetime.now(timezone.utc)
        schema = PokemonSchema.model_validate(
            {
                "id": uuid4(),
                "hp": 45,
                "name": "bulbasaur",
                "order": 1,
                "speed": 45,
                "height": 7,
                "weight": 69,
                "status": PokemonStatusEnum.INCOMPLETE,
                "attack": 49,
                "defense": 49,
                "is_baby": False,
                "gender_rate": 1,
                "is_mythical": False,
                "description": None,
                "is_legendary": False,
                "capture_rate": 45,
                "hatch_counter": 20,
                "base_happiness": 70,
                "external_image": "url",
                "special_attack": 65,
                "special_defense": 65,
                "base_experience": 64,
                "evolution_chain": None,
                "evolves_from_species": None,
                "has_gender_differences": False,
                "created_at": now,
                "updated_at": None,
                "deleted_at": None,
                "types": [],
                "moves": [],
                "abilities": [],
                "evolutions": [],
                "encounters": [],
                "shape": None,
                "habitat": None,
                "growth_rate": None,
            }
        )

        assert schema.name == "bulbasaur"
