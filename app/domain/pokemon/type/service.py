from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.type.business import (
    ensure_badges,
    ensure_colors,
    ensure_damage_relations,
)

from app.domain.pokemon.type.repository import TypeRepository
from app.domain.pokemon.type.schema import (
    TypeSchema,
    TypeSyncResourceSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.infrastructure.external_api.schemas import NamedExternalResourceSchema
from app.models import Type, PokemonStatusEnum
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class TypeService(BaseService[TypeRepository, Type]):
    def __init__(
        self,
        repository: TypeRepository,
        client: PokeApiClient | None = None,
    ) -> None:
        super().__init__(
            alias="Type",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="TypeService", operation="pokemon.type"
            ),
            schema_class=TypeSchema,
            cache_prefix="type",
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(TypeRepository(session), client)

    async def sync_from_resources(self, resources: list[dict]) -> list[Type]:
        synced: list[TypeSyncResourceSchema] = []
        for entry in resources:
            resource = entry.get("type") or entry
            name = resource["name"]
            url = resource.get("url")

            order = ensure_order_number(url)
            resource = await self.get_or_create(name=name, order=order, url=url)

            if not resource:
                continue

            synced.append(resource)

        type_synced: list[Type] = []
        for resource in synced:
            type_damages = await self.update_damages(
                resource=resource.type,
                type_strengths=resource.type_strengths,
                type_weaknesses=resource.type_weaknesses,
            )
            type_synced.append(type_damages)

        return type_synced

    async def get_or_create(
        self,
        order: int,
        url: str | None = None,
        name: str | None = None,
        status: PokemonStatusEnum = PokemonStatusEnum.INCOMPLETE,
    ) -> TypeSyncResourceSchema | None:
        entity = await self.repository.find_by(order=order)
        if entity:
            return TypeSyncResourceSchema(
                type=entity,
                type_strengths=[],
                type_weaknesses=[],
            )
        if name is None:
            raise ValueError("Name cannot be None when creating a new PokemonType")

        external_type = await self.client.get_type(name_or_id=name)

        if external_type is None:
            raise ValueError(f"Failed to retrieve external type for name: {name}")

        move_damage_class_url = (
            external_type.move_damage_class.url
            if external_type.move_damage_class is not None
            else None
        )
        description = await self._update_description(
            type_class_url=move_damage_class_url
        )
        badges = ensure_badges(external_type.sprites)
        pokemon_type_colors = ensure_colors(name)
        damage_relations = ensure_damage_relations(external_type.damage_relations)

        saved_type = await self.repository.save(
            entity=Type(
                url=url,
                name=name,
                order=order,
                status=status,
                badge_url=badges.badge_url,
                text_color=pokemon_type_colors.text_color,
                description=description,
                badge_icon_url=badges.badge_icon_url,
                badge_shield_url=badges.badge_shield_url,
                background_color=pokemon_type_colors.background_color,
                badge_legends_url=badges.badge_legends_url,
                badge_shield_icon_url=badges.badge_shield_icon_url,
                badge_legend_icon_url=badges.badge_legend_icon_url,
            )
        )

        if not damage_relations:
            return TypeSyncResourceSchema(
                type=saved_type,
                type_weaknesses=[],
                type_strengths=[],
            )

        return TypeSyncResourceSchema(
            type=saved_type,
            type_weaknesses=damage_relations.weaknesses,
            type_strengths=damage_relations.strengths,
        )

    async def _update_description(
        self, type_class_url: str | None, description: str | None = None
    ) -> str:
        if description and description != "":
            return description
        if not type_class_url:
            return ""
        external_move_damage_class = await self.client.get_move_damage_class_by_url(
            type_class_url
        )
        if external_move_damage_class:
            description_entry = get_text_language(
                entries=external_move_damage_class.descriptions, title="description"
            )
            return description_entry.text
        return ""

    async def update_damages(
        self,
        resource: Type,
        type_strengths: list[NamedExternalResourceSchema],
        type_weaknesses: list[NamedExternalResourceSchema],
    ) -> Type:
        change: bool = False
        strengths = await self.sync_from_damages(type_strengths)
        weaknesses = await self.sync_from_damages(type_weaknesses)

        if weaknesses:
            resource.weaknesses = weaknesses
            change = True

        if strengths:
            resource.strengths = strengths
            change = True

        if change:
            resource.status = PokemonStatusEnum.COMPLETE
            return await self.repository.update(resource)

        return resource

    async def sync_from_damages(
        self, sync_resource: list[NamedExternalResourceSchema]
    ) -> list[Type]:
        damages: list[Type] = []
        for resource in sync_resource:
            name = resource.name
            url = resource.url
            order = ensure_order_number(url)

            resource_damage = await self.get_or_create(url=url, name=name, order=order)

            if not resource_damage:
                continue

            damages.append(resource_damage.type)

        return damages
