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
    def _serialize_images(images: object) -> list[str]:
        if isinstance(images, list):
            return [str(item) for item in images if item]

        if isinstance(images, str):
            cleaned = images.strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed if item]
                except json.JSONDecodeError:
                    return []
            if cleaned.startswith("{") and cleaned.endswith("}"):
                content = cleaned[1:-1].strip()
                if not content:
                    return []
                return [
                    item.strip().strip('"')
                    for item in content.split(",")
                    if item.strip()
                ]
            if cleaned:
                return [cleaned]

        return []


class GetImageSourceResultSchema(BaseModel):
    image: str
    source: str
