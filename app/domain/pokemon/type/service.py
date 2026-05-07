from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.type.business import (
    ensure_colors,
    ensure_badges,
    ensure_damage_relations,
)
from app.domain.pokemon.type.repository import PokemonTypeRepository
from app.domain.pokemon.type.schema import (
    PokemonTypeSchema,
    PokemonTypeSyncResourceSchema,
)
from app.infrastructure.external_api import PokeApiClient
from app.infrastructure.external_api.schemas import NamedExternalResourceSchema
from app.models import PokemonType, PokemonStatusEnum
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class PokemonTypeService(BaseService[PokemonTypeRepository, PokemonType]):
    def __init__(
        self, repository: PokemonTypeRepository, client: PokeApiClient | None = None
    ) -> None:
        super().__init__(
            alias="PokemonType",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokemonTypeService", operation="type"
            ),
            schema_class=PokemonTypeSchema,
        )
        self.client = client or PokeApiClient()

    @classmethod
    def from_session(cls, session: AsyncSession, client: PokeApiClient | None = None):
        return cls(PokemonTypeRepository(session), client)

    async def sync_from_resources(self, resources: list[dict]) -> list[PokemonType]:
        synced: list[PokemonTypeSyncResourceSchema] = []
        for entry in resources:
            resource = entry.get("type") or entry
            name = resource["name"]
            url = resource.get("url")

            order = ensure_order_number(url)
            resource = await self.get_or_create(name=name, order=order, url=url)

            if not resource:
                continue

            synced.append(resource)

        pokemon_type_synced: list[PokemonType] = []
        for resource in synced:
            pokemon_type_damages = await self.update_damages(
                pokemon_type=resource.pokemon_type,
                pokemon_type_weaknesses=resource.pokemon_type_weaknesses,
                pokemon_type_strengths=resource.pokemon_type_strengths,
            )

            pokemon_type_synced.append(pokemon_type_damages)

        return pokemon_type_synced

    async def sync_from_damages(
        self, sync_resource: list[NamedExternalResourceSchema]
    ) -> list[PokemonType]:

        damages: list[PokemonType] = []
        for resource in sync_resource:
            name = resource.name
            url = resource.url
            order = ensure_order_number(url)

            resource_damage = await self.get_or_create(
                name=name, order=order, url=url, status=PokemonStatusEnum.INCOMPLETE
            )

            if not resource_damage:
                continue

            damages.append(resource_damage.pokemon_type)

        return damages

    async def get_or_create(
        self,
        order: int,
        url: str | None = None,
        name: str | None = None,
        status: PokemonStatusEnum = PokemonStatusEnum.INCOMPLETE,
    ) -> PokemonTypeSyncResourceSchema | None:
        entity = await self.repository.find_by(order=order)
        if entity:
            return PokemonTypeSyncResourceSchema(
                pokemon_type=entity,
                pokemon_type_weaknesses=[],
                pokemon_type_strengths=[],
            )
        if name is None:
            raise ValueError("Name cannot be None when creating a new PokemonType")

        external_type = await self.client.get_type(name)
        if external_type is None:
            raise ValueError(f"Failed to retrieve external type for name: {name}")

        move_damage_class_url = (
            external_type.move_damage_class.url
            if external_type.move_damage_class is not None
            else None
        )
        description = await self.update_description(
            type_class_url=move_damage_class_url
        )
        badges = ensure_badges(external_type.sprites)
        pokemon_type_colors = ensure_colors(name)
        damage_relations = ensure_damage_relations(external_type.damage_relations)
        saved_pokemon_type = await self.repository.save(
            entity=PokemonType(
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
            return PokemonTypeSyncResourceSchema(
                pokemon_type=saved_pokemon_type,
                pokemon_type_weaknesses=[],
                pokemon_type_strengths=[],
            )
        return PokemonTypeSyncResourceSchema(
            pokemon_type=saved_pokemon_type,
            pokemon_type_weaknesses=damage_relations.weaknesses,
            pokemon_type_strengths=damage_relations.strengths,
        )

    async def update_damages(
        self,
        pokemon_type: PokemonType,
        pokemon_type_weaknesses: list[NamedExternalResourceSchema],
        pokemon_type_strengths: list[NamedExternalResourceSchema],
    ) -> PokemonType:
        change: bool = False
        weaknesses = await self.sync_from_damages(pokemon_type_weaknesses)
        strengths = await self.sync_from_damages(pokemon_type_strengths)

        if weaknesses:
            pokemon_type.weaknesses = weaknesses
            change = True

        if strengths:
            pokemon_type.strengths = strengths
            change = True

        if change:
            pokemon_type.status = PokemonStatusEnum.COMPLETE
            return await self.repository.update(pokemon_type)

        return pokemon_type

    async def update_description(
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

    async def find_one(
        self,
        param: str,
        user_request: str | None = None,
    ):
        pokemon_type = await super().find_one(param, user_request)
        if pokemon_type.status == PokemonStatusEnum.INCOMPLETE:
            if not pokemon_type.description or pokemon_type.description == "":
                pokemon_type.description = await self.update_description(
                    type_class_url=pokemon_type.url
                )
            external_type = await self.client.get_type(pokemon_type.name)
            if external_type is None:
                raise ValueError(
                    f"Failed to retrieve external type for name: {pokemon_type.name}"
                )
            damage_relations = ensure_damage_relations(external_type.damage_relations)
            if not damage_relations:
                return pokemon_type
            await self.cache_service.delete_domain()
            return await self.update_damages(
                pokemon_type=pokemon_type,
                pokemon_type_weaknesses=damage_relations.weaknesses,
                pokemon_type_strengths=damage_relations.strengths,
            )
        return pokemon_type
