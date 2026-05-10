from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Annotated

from fastapi import HTTPException, Query

from app.core.cache.service import CacheService
from app.core.exceptions import handle_service_exception
from app.core.logging import LoggingParams
from app.core.pagination import CustomLimitOffsetPage
from app.core.service.base import BaseService
from app.domain.pokemon.business import (
    build_external_image,
    first_english_flavor_text,
    stats_by_name,
    result_list_cache_serialize,
    result_cache_serialize,
)
from app.domain.pokemon.ability.service import PokemonAbilityService
from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.schema import (
    PokemonSchema,
)

from app.domain.pokemon.encounter.service import PokemonEncounterService
from app.domain.pokemon.growth_rate.service import PokemonGrowthRateService
from app.domain.pokemon.habitat.service import PokemonHabitatService
from app.domain.pokemon.image.service import PokemonImageService
from app.domain.pokemon.move.service import PokemonMoveService
from app.domain.pokemon.shape.service import PokemonShapeService
from app.domain.pokemon.type.service import PokemonTypeService
from app.infrastructure.external_api import PokeApiClient
from app.models import Pokemon
from app.models.enums import PokemonStatusEnum
from app.shared.schemas import FilterPage
from app.shared.utils.number import ensure_order_number

logger = logging.getLogger(__name__)


class PokemonService(BaseService[PokemonRepository, Pokemon]):
    def __init__(
        self,
        repository: PokemonRepository,
        *,
        client: PokeApiClient | None = None,
        type_service: PokemonTypeService | None = None,
        ability_service: PokemonAbilityService | None = None,
        move_service: PokemonMoveService | None = None,
        image_service: PokemonImageService | None = None,
        growth_rate_service: PokemonGrowthRateService | None = None,
        habitat_service: PokemonHabitatService | None = None,
        shape_service: PokemonShapeService | None = None,
        encounter_service: PokemonEncounterService | None = None,
    ) -> None:
        super().__init__(
            alias="Pokemon",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokemonService", operation="pokemon"
            ),
            schema_class=PokemonSchema,
            cache_prefix="pokemon",
        )
        self.client = client or PokeApiClient()
        self.list_cache_service = CacheService(
            alias="PokemonList",
            prefix="pokemon",
            logger_params=LoggingParams(
                logger=logger, service="PokemonService", operation="pokemon_list"
            ),
            schema_class=PokemonSchema,
        )
        session = repository.session
        self.type_service = type_service or PokemonTypeService.from_session(
            session, self.client
        )
        self.ability_service = ability_service or PokemonAbilityService.from_session(
            session, self.client
        )
        self.move_service = move_service or PokemonMoveService.from_session(
            session, self.client
        )
        self.image_service = image_service or PokemonImageService.from_session(session)
        self.growth_rate_service = (
            growth_rate_service
            or PokemonGrowthRateService.from_session(session, self.client)
        )
        self.habitat_service = habitat_service or PokemonHabitatService.from_session(
            session, self.client
        )
        self.shape_service = shape_service or PokemonShapeService.from_session(
            session, self.client
        )
        self.encounter_service = (
            encounter_service
            or PokemonEncounterService.from_session(session, self.client)
        )

    async def _ensure_initial_catalog(self) -> None:
        if await self.repository.has_any():
            return
        external_list = await self.client.list_pokemon(offset=0, limit=1350)
        for resource in external_list.results:
            order = ensure_order_number(resource.url)
            existing = await self.repository.get_by_order(order)
            if existing:
                continue
            await self.repository.create_minimal(
                name=resource.name,
                order=order,
                external_image=build_external_image(order),
            )
        await self.repository.session.commit()

    def _list_key(self, page_filter: FilterPage | None) -> str:
        filter_page = FilterPage.build(page_filter)
        return self.list_cache_service.cache.build_key(
            "pokemon", "list", filter_page.model_dump()
        )

    def _detail_key(self, identifier: str) -> str:
        return self.cache_service.cache.build_key("pokemon", "detail", identifier)

    async def _invalidate_cache(self, identifier: str | None = None) -> None:
        await self.list_cache_service.cache.delete_pattern("pokemon:list*")
        if identifier:
            await self.cache_service.cache.delete_cache(self._detail_key(identifier))

    async def list_all(
        self,
        page_filter: Annotated[FilterPage, Query()] = None,
        user_request: str | None = None,
        trainer_id: str | None = None,
    ) -> list[PokemonSchema] | CustomLimitOffsetPage[PokemonSchema] | None:
        try:
            await self._ensure_initial_catalog()
            result = await self.repository.list_all(page_filter=page_filter)
            return result
        except Exception as exception:
            handle_service_exception(
                exception,
                logger=logger,
                service="PokemonService",
                operation="list_all",
                raise_exception=True,
            )

    async def list_all_cached(
        self,
        page_filter: Annotated[FilterPage, Query()] = None,
        user_request: str | None = None,
        trainer_id: str | None = None,
    ):
        try:
            clean_cache = page_filter.clean_cache if page_filter else False

            if clean_cache:
                await self.cache_service.delete_domain()
            if page_filter:
                page_filter.clean_cache = None
            key = self._list_key(page_filter)
            cached = await self.list_cache_service.get_list(key)
            if cached:
                return cached
            data = await self.list_all(
                page_filter=page_filter,
                user_request=user_request,
                trainer_id=trainer_id,
            )
            if data is not None:
                await self.list_cache_service.set_list(
                    key, data, result_list_cache_serialize
                )
            return data
        except Exception as exception:
            handle_service_exception(
                exception,
                logger=logger,
                service="PokemonService",
                operation="list_all",
                raise_exception=True,
            )

    async def _enrich_if_needed(
        self, pokemon: Pokemon, with_evolutions: bool = True
    ) -> Pokemon:
        if pokemon.status == PokemonStatusEnum.COMPLETE:
            return pokemon

        payload = (await self.client.get_pokemon(pokemon.name)).model_dump()
        species = (await self.client.get_pokemon_species(pokemon.name)).model_dump()
        encounters = await self.client.get_pokemon_encounters(pokemon.order)
        stats = stats_by_name(payload)

        pokemon.height = payload.get("height")
        pokemon.weight = payload.get("weight")
        pokemon.base_experience = payload.get("base_experience")
        pokemon.hp = stats.get("hp")
        pokemon.attack = stats.get("attack")
        pokemon.defense = stats.get("defense")
        pokemon.special_attack = stats.get("special_attack")
        pokemon.special_defense = stats.get("special_defense")
        pokemon.speed = stats.get("speed")
        pokemon.description = first_english_flavor_text(
            species.get("flavor_text_entries")
        )
        pokemon.capture_rate = species.get("capture_rate")
        pokemon.is_baby = species.get("is_baby")
        pokemon.is_mythical = species.get("is_mythical")
        pokemon.is_legendary = species.get("is_legendary")
        pokemon.gender_rate = species.get("gender_rate")
        pokemon.hatch_counter = species.get("hatch_counter")
        pokemon.base_happiness = species.get("base_happiness")
        pokemon.has_gender_differences = species.get("has_gender_differences")
        pokemon.evolves_from_species = (species.get("evolves_from_species") or {}).get(
            "name"
        )
        pokemon.evolution_chain = (species.get("evolution_chain") or {}).get("url")

        pokemon.types.clear()
        pokemon.types.extend(
            await self.type_service.sync_from_resources(payload.get("types", []))
        )

        pokemon.moves.clear()
        pokemon.moves.extend(
            await self.move_service.sync_from_resources(payload.get("moves", []))
        )

        pokemon.abilities.clear()
        pokemon.abilities.extend(
            await self.ability_service.sync_from_resources(payload.get("abilities", []))
        )

        pokemon.encounters.clear()
        pokemon.encounters.extend(
            await self.encounter_service.sync_from_payload(encounters)
        )

        growth_rate = await self.growth_rate_service.sync_from_resource(
            species.get("growth_rate")
        )
        pokemon.growth_rate_id = growth_rate.id if growth_rate else None

        habitat = await self.habitat_service.sync_from_resource(species.get("habitat"))
        pokemon.habitat_id = habitat.id if habitat else None

        shape = await self.shape_service.sync_from_resource(species.get("shape"))
        pokemon.shape_id = shape.id if shape else None

        images = await self.image_service.sync_from_sprites(
            pokemon.order, payload.get("sprites")
        )
        pokemon.images_id = images.id if images else None

        if with_evolutions:
            evolutions = await self._sync_evolution_chain(pokemon)
            pokemon.evolutions = evolutions

        pokemon.status = PokemonStatusEnum.COMPLETE
        await self.repository.session.commit()
        await self._invalidate_cache(pokemon.name)
        return await self.repository.find_detail(str(pokemon.id)) or pokemon

    async def _sync_evolution_chain(self, pokemon: Pokemon) -> list[Pokemon]:
        if not pokemon.evolution_chain:
            return []
        chain_payload = (
            await self.client.get_evolution_chain_by_url(pokemon.evolution_chain)
        ).model_dump()
        names = self._collect_evolution_names(chain_payload.get("chain"))
        pokemons = await self.repository.list_by_names(names)
        return [candidate for candidate in pokemons if candidate.id != pokemon.id]

    def _collect_evolution_names(self, node: dict | None) -> set[str]:
        if not node:
            return set()
        names = {node["species"]["name"]}
        for child in node.get("evolves_to", []):
            names.update(self._collect_evolution_names(child))
        return names

    async def find_detail(self, identifier: str) -> Pokemon:
        try:
            key = self._detail_key(identifier)
            cached = await self.cache_service.get_one(key)
            if cached:
                return cached

            await self._ensure_initial_catalog()
            pokemon = await self.repository.find_detail(identifier)
            if pokemon is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, detail="Pokemon not found"
                )
            pokemon = await self._enrich_if_needed(pokemon)

            await self.cache_service.set_one(key, pokemon, result_cache_serialize)
            return pokemon
        except Exception as exception:
            handle_service_exception(
                exception,
                logger=logger,
                service="PokemonService",
                operation="find_detail",
                raise_exception=True,
            )
