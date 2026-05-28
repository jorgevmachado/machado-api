from __future__ import annotations

from app.domain.trainer.owned_pokemon.schema import OwnedPokemonSchema


def test_serialize_collection_keeps_empty_values_untouched() -> None:
    payload = {"moves": []}
    OwnedPokemonSchema._serialize_collection(payload, "moves", OwnedPokemonSchema)
    assert payload == {"moves": []}


def test_serialize_collection_serializes_model_dump() -> None:
    class DummyModel:
        @staticmethod
        def model_validate(value):
            class _Validated:
                def __init__(self, data):
                    self.data = data

                def model_dump(self, mode="json"):
                    return {"value": self.data}

                def serialize(self):
                    return {"serialized": self.data}

            return _Validated(value)

    payload = {"moves": ["a", "b"]}
    OwnedPokemonSchema._serialize_collection(payload, "moves", DummyModel)
    assert payload["moves"] == [{"value": "a"}, {"value": "b"}]


def test_serialize_collection_serializes_with_serialize_flag() -> None:
    class DummyModel:
        @staticmethod
        def model_validate(value):
            class _Validated:
                def __init__(self, data):
                    self.data = data

                def model_dump(self, mode="json"):
                    return {"value": self.data}

                def serialize(self):
                    return {"serialized": self.data}

            return _Validated(value)

    payload = {"moves": ["x"]}
    OwnedPokemonSchema._serialize_collection(
        payload,
        "moves",
        DummyModel,
        use_serialize=True,
    )
    assert payload["moves"] == [{"serialized": "x"}]
