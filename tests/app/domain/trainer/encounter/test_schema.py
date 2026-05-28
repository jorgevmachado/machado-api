from __future__ import annotations

from app.domain.trainer.encounter.schema import TrainerEncounterSchema


def test_serialize_collection_keeps_empty_values_untouched() -> None:
    payload = {"items": []}
    TrainerEncounterSchema._serialize_collection(payload, "items", TrainerEncounterSchema)
    assert payload == {"items": []}


def test_serialize_collection_serializes_values_with_model_dump() -> None:
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

    payload = {"items": [1, 2]}
    TrainerEncounterSchema._serialize_collection(payload, "items", DummyModel)

    assert payload["items"] == [{"value": 1}, {"value": 2}]


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

    payload = {"items": [1]}
    TrainerEncounterSchema._serialize_collection(
        payload,
        "items",
        DummyModel,
        use_serialize=True,
    )

    assert payload["items"] == [{"serialized": 1}]
