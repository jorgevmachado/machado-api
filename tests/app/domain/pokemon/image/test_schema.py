from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.domain.pokemon.image.schema import ImageSchema


class TestImageSchema:
    @staticmethod
    def test_normalize_images_from_json_string() -> None:
        now = datetime.now(timezone.utc)
        schema = ImageSchema.model_validate(
            {
                "id": uuid4(),
                "order": 1,
                "images": '["a", "b"]',
                "back_image": "back",
                "front_image": "front",
                "back_source": "back_default",
                "front_source": "front_default",
                "created_at": now,
                "updated_at": None,
                "deleted_at": None,
            }
        )

        assert schema.images == ["a", "b"]

    @staticmethod
    def test_normalize_images_from_brace_wrapped_string() -> None:
        result = ImageSchema._serialize_images('{"a","b"}')

        assert result == ["a", "b"]

    @staticmethod
    def test_normalize_images_from_plain_string_and_invalid_json() -> None:
        assert ImageSchema._serialize_images("single-url") == ["single-url"]
        assert ImageSchema._serialize_json_images("[invalid") is None

    @staticmethod
    def test_serialize_json_images_returns_empty_list_for_invalid_json_array() -> None:
        assert ImageSchema._serialize_json_images("[invalid]") == []

    @staticmethod
    def test_serialize_brace_wrapped_images_returns_empty_list_for_empty_content() -> (
        None
    ):
        assert ImageSchema._serialize_brace_wrapped_images("{}") == []

    @staticmethod
    def test_serialize_string_images_returns_empty_list_for_blank_text() -> None:
        assert ImageSchema._serialize_string_images("   ") == []

    @staticmethod
    def test_serialize_images_returns_empty_for_unsupported_type() -> None:
        assert ImageSchema._serialize_images(123) == []

    @staticmethod
    def test_serialize_returns_json_ready_payload() -> None:
        now = datetime.now(timezone.utc)
        schema = ImageSchema.model_validate(
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
        )

        serialized = schema.serialize()

        assert serialized["images"] == ["a"]
