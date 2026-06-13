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
from app.domain.pokemon.type.schema import TypeSchema
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

    async def find_one(
        self,
        param: str,
        **kwargs,
    ) -> Type | None:
        entity = await super().find_one(param, **kwargs)

        if entity and entity.status != PokemonStatusEnum.COMPLETE:
            return await self._sync_external(entity=entity)

        return entity

    async def sync_from_resources(self, resources: list[dict]) -> list[Type]:
        type_synced: list[Type] = []
        for entry in resources:
            resource = entry.get("type") or entry
            url = resource.get("url")
            order = ensure_order_number(url)
            entity = await self.get_or_create(order=order, url=url)
            type_synced.append(entity)
        return type_synced

    async def _sync_external(
        self,
        url: str | None = None,
        order: int | None = None,
        entity: Type | None = None,
        with_damages: bool | None = True,
    ) -> Type:
        url = entity.url if entity else url
        order = entity.order if entity else order

        if not order:
            raise ValueError("Order is required to sync external type")

        if not url:
            raise ValueError("URL is required to sync external type")

        external_type = await self.client.get_type(name_or_id=order)
        if external_type is None:
            raise ValueError(f"Failed to retrieve external type for order: {order}")
        if entity:
            entity_to_persist = entity
        else:
            name = external_type.name
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
            entity_to_persist = await self.repository.save(
                entity=Type(
                    url=url,
                    name=name,
                    order=order,
                    status=PokemonStatusEnum.INCOMPLETE,
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

        damage_relations = (
            ensure_damage_relations(external_type.damage_relations)
            if with_damages
            else None
        )

        if not damage_relations:
            return entity_to_persist

        return await self._add_damage_relations(
            entity=entity_to_persist,
            type_strengths=damage_relations.strengths,
            type_weaknesses=damage_relations.weaknesses,
        )

    async def get_or_create(
        self, order: int, url: str | None = None, with_damages: bool | None = True
    ) -> Type:
        entity = await self.repository.find_by(order=order)

        if entity and entity.status == PokemonStatusEnum.COMPLETE:
            return entity

        return await self._sync_external(
            url=url, order=order, entity=entity, with_damages=with_damages
        )

    async def _add_damage_relations(
        self,
        entity: Type,
        type_strengths: list[NamedExternalResourceSchema],
        type_weaknesses: list[NamedExternalResourceSchema],
    ) -> Type:
        change: bool = False

        strengths = await self._sync_from_damages(type_strengths)
        weaknesses = await self._sync_from_damages(type_weaknesses)

        if strengths:
            entity.strengths = strengths
            change = True

        if weaknesses:
            entity.weaknesses = weaknesses
            change = True

        if change:
            entity.status = PokemonStatusEnum.COMPLETE
            return await self.repository.update(entity)

        return entity

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

    async def _sync_from_damages(
        self, sync_resource: list[NamedExternalResourceSchema]
    ) -> list[Type]:
        damages: list[Type] = []
        for resource in sync_resource:
            url = resource.url
            order = ensure_order_number(url)

            resource_damage = await self.get_or_create(
                url=url, order=order, with_damages=False
            )

            if not resource_damage:
                continue

            damages.append(resource_damage)

        return damages
