from datetime import datetime
import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class PokemonSpritesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PokemonImageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order: int
    images: list[str]
    back_image: str
    front_image: str
    back_source: str
    front_source: str
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    @field_validator("images", mode="before")
    @classmethod
    def normalize_images(cls, images: object) -> list[str]:
        return cls._serialize_images(images)

    def serialize(self) -> dict:
        serialized = self.model_dump(mode="json")
        return serialized

    @staticmethod
    def _serialize_json_images(cleaned: str) -> list[str] | None:
        if not (cleaned.startswith("[") and cleaned.endswith("]")):
            return None

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        return [str(item) for item in parsed if item]

    @staticmethod
    def _serialize_brace_wrapped_images(cleaned: str) -> list[str] | None:
        if not (cleaned.startswith("{") and cleaned.endswith("}")):
            return None

        content = cleaned[1:-1].strip()
        if not content:
            return []

        if ":" in content:
            return []

        return [item.strip().strip('"') for item in content.split(",") if item.strip()]

    @classmethod
    def _serialize_string_images(cls, images: str) -> list[str]:
        cleaned = images.strip()
        if not cleaned:
            return []

        json_images = cls._serialize_json_images(cleaned)
        if json_images is not None:
            return json_images

        brace_wrapped_images = cls._serialize_brace_wrapped_images(cleaned)
        if brace_wrapped_images is not None:
            return brace_wrapped_images

        return [cleaned]

    @staticmethod
    def _serialize_images(images: object) -> list[str]:
        if isinstance(images, list):
            return [str(item) for item in images if item]

        if isinstance(images, str):
            return PokemonImageSchema._serialize_string_images(images)

        return []


class GetImageSourceResultSchema(BaseModel):
    image: str
    source: str
