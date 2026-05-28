from datetime import datetime
from dataclasses import dataclass, field
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import Type, PokemonStatusEnum
from app.infrastructure.external_api.schemas import NamedExternalResourceSchema


class TypeDamageSchema(BaseModel):
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


class TypeSchema(TypeDamageSchema):
    model_config = ConfigDict(from_attributes=True)
    strengths: list[TypeDamageSchema] = []
    weaknesses: list[TypeDamageSchema] = []

    def serialize(self):
        serialized = self.model_dump(mode="json")
        if "weaknesses" in serialized and serialized["weaknesses"]:
            serialized["weaknesses"] = [
                TypeDamageSchema.model_validate(weakness).model_dump(mode="json")
                for weakness in serialized["weaknesses"]
            ]
        if "strengths" in serialized and serialized["strengths"]:
            serialized["strengths"] = [
                TypeDamageSchema.model_validate(strength).model_dump(mode="json")
                for strength in serialized["strengths"]
            ]
        return serialized


class TypeColorSchema(BaseModel):
    id: int
    name: str
    text_color: str
    background_color: str


class TypeBadgeSchema(BaseModel):
    badge_url: str
    badge_icon_url: str
    badge_shield_url: str
    badge_legends_url: str
    badge_legend_icon_url: str
    badge_shield_icon_url: str


@dataclass(slots=True)
class TypeSyncResourceSchema:
    type: Type
    type_weaknesses: list[NamedExternalResourceSchema] = field(default_factory=list)
    type_strengths: list[NamedExternalResourceSchema] = field(default_factory=list)


@dataclass(slots=True)
class EnsureDamageRelationsResultSchema:
    weaknesses: list[NamedExternalResourceSchema] = field(default_factory=list)
    strengths: list[NamedExternalResourceSchema] = field(default_factory=list)
