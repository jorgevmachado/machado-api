from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.infrastructure.external_api.schemas import NamedExternalResourceSchema
from app.models import PokemonType, PokemonStatusEnum


class PokemonTypeDamageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str | None = None
    name: str
    order: int | None = None
    status: PokemonStatusEnum | None = None
    text_color: str | None = None
    badge_url: str | None = None
    description: str | None = None
    badge_icon_url: str | None = None
    background_color: str | None = None
    badge_shield_url: str | None = None
    badge_legends_url: str | None = None
    badge_legend_icon_url: str | None = None
    badge_shield_icon_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class PokemonTypeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    name: str
    order: int
    text_color: str
    badge_url: str | None = None
    strengths: list[PokemonTypeDamageSchema] = []
    weaknesses: list[PokemonTypeDamageSchema] = []
    description: str | None = None
    badge_icon_url: str | None = None
    background_color: str | None = None
    badge_shield_url: str | None = None
    badge_legends_url: str | None = None
    badge_legend_icon_url: str | None = None
    badge_shield_icon_url: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    def serialize(self):
        serialized = self.model_dump(mode="json")
        if "weaknesses" in serialized and serialized["weaknesses"]:
            serialized["weaknesses"] = [
                PokemonTypeDamageSchema.model_validate(weakness).model_dump(mode="json")
                for weakness in serialized["weaknesses"]
            ]
        if "strengths" in serialized and serialized["strengths"]:
            serialized["strengths"] = [
                PokemonTypeDamageSchema.model_validate(strength).model_dump(mode="json")
                for strength in serialized["strengths"]
            ]
        return serialized


class PokemonTypeColorSchema(BaseModel):
    id: int
    name: str
    text_color: str
    background_color: str


class PokemonTypeBadgeSchema(BaseModel):
    badge_url: str
    badge_icon_url: str
    badge_shield_url: str
    badge_legends_url: str
    badge_legend_icon_url: str
    badge_shield_icon_url: str


@dataclass(slots=True)
class PokemonTypeSyncResourceSchema:
    pokemon_type: PokemonType
    pokemon_type_weaknesses: list[NamedExternalResourceSchema] = field(
        default_factory=list
    )
    pokemon_type_strengths: list[NamedExternalResourceSchema] = field(
        default_factory=list
    )


@dataclass(slots=True)
class EnsureDamageRelationsResultSchema:
    weaknesses: list[NamedExternalResourceSchema] = field(default_factory=list)
    strengths: list[NamedExternalResourceSchema] = field(default_factory=list)
