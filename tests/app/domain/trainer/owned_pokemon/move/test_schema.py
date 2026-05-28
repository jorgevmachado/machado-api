from __future__ import annotations

from app.domain.trainer.owned_pokemon.move.schema import OwnedPokemonMoveSchema


def test_serialize_collection_keeps_empty_values_untouched() -> None:
    payload = {"moves": []}
    OwnedPokemonMoveSchema._serialize_collection(payload, "moves", OwnedPokemonMoveSchema)
    assert payload == {"moves": []}


def test_serialize_collection_serializes_values() -> None:
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

    payload = {"moves": [10]}
    OwnedPokemonMoveSchema._serialize_collection(payload, "moves", DummyModel)
    assert payload["moves"] == [{"value": 10}]


def test_serialize_collection_serializes_values_with_serialize_flag() -> None:
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

    payload = {"moves": [20]}
    OwnedPokemonMoveSchema._serialize_collection(
        payload,
        "moves",
        DummyModel,
        use_serialize=True,
    )
    assert payload["moves"] == [{"serialized": 20}]
