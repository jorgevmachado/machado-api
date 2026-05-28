from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Annotated

from fastapi import HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import handle_service_exception
from app.core.logging import LoggingParams, log_service_success
from app.core.pagination import CustomLimitOffsetPage
from app.core.service.base import BaseService
from app.domain.pokemon.ability.service import AbilityService
from app.domain.pokemon.business import stats_by_name, collect_evolution_names
from app.domain.pokemon.encounter.service import EncounterService
from app.domain.pokemon.growth_rate.service import GrowthRateService
from app.domain.pokemon.habitat.service import HabitatService
from app.domain.pokemon.image.service import ImageService
from app.domain.pokemon.move.service import MoveService
from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.schema import (
    PokemonSchema,
)
from app.domain.pokemon.shape.service import ShapeService
from app.domain.pokemon.type.service import TypeService
from app.infrastructure.external_api import PokeApiClient
from app.models import Pokemon, PokemonStatusEnum
from app.shared.schemas import FilterPage
from app.shared.utils.image import ensure_external_image
from app.shared.utils.number import ensure_order_number
from app.shared.utils.string import get_text_language

logger = logging.getLogger(__name__)


class PokemonService(BaseService[PokemonRepository, Pokemon]):
    def __init__(
        self,
        repository: PokemonRepository,
        *,
        client: PokeApiClient | None = None,
        type_service: TypeService | None = None,
        ability_service: AbilityService | None = None,
        move_service: MoveService | None = None,
        image_service: ImageService | None = None,
        growth_rate_service: GrowthRateService | None = None,
        habitat_service: HabitatService | None = None,
        shape_service: ShapeService | None = None,
        encounter_service: EncounterService | None = None,
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
        session = repository.session
        self.type_service = type_service or TypeService.from_session(
            session, self.client
        )
        self.ability_service = ability_service or AbilityService.from_session(
            session, self.client
        )
        self.move_service = move_service or MoveService.from_session(
            session, self.client
        )
        self.image_service = image_service or ImageService.from_session(session)
        self.growth_rate_service = (
            growth_rate_service or GrowthRateService.from_session(session, self.client)
        )
        self.habitat_service = habitat_service or HabitatService.from_session(
            session, self.client
        )
        self.shape_service = shape_service or ShapeService.from_session(
            session, self.client
        )
        self.encounter_service = encounter_service or EncounterService.from_session(
            session, self.client
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(PokemonRepository(session))

    async def list_all(
        self,
        page_filter: Annotated[FilterPage, Query()] = None,
        user_request: str | None = None,
    ) -> list[Pokemon] | CustomLimitOffsetPage[Pokemon] | None:
        await self._ensure_initial_catalog()
        return await super().list_all(
            page_filter=page_filter, user_request=user_request
        )

    async def list_all_cached(
        self, page_filter: Annotated[FilterPage, Query()] = None, **kwargs
    ) -> list[Pokemon] | CustomLimitOffsetPage[Pokemon] | None:

        clean_cache = page_filter.clean_cache if page_filter else False
        if clean_cache:
            await self.cache_service.delete_cache(
                without=[self.cache_service.build_key_one(param="meta")],
            )
        if page_filter:
            page_filter.clean_cache = None
        key = self.cache_service.build_key_list(page_filter=page_filter)
        cached = await self.cache_service.get_list(key)
        if cached:
            return cached
        result = await self.list_all(page_filter=page_filter, **kwargs)

        await self.cache_service.set_list(key, result)

        return result

    async def _ensure_initial_catalog(self):
        cache_key = self.cache_service.build_key_one(param="meta")
        cached_meta = await self.cache_service.get_cache(key=cache_key)
        if cached_meta:
            return

        db_total = await self.repository.total()
        external_total = await self.client.total_pokemon()
        if db_total == 0 or external_total > db_total:
            external_list = await self.client.list_pokemon(
                offset=0, limit=external_total
            )
            db_total = external_list.count
            for resource in external_list.results:
                order = ensure_order_number(url=resource.url)
                existing = await self.repository.find_by(order=order)
                if existing:
                    continue
                await self.repository.save(
                    entity=Pokemon(
                        order=order,
                        name=resource.name,
                        external_image=ensure_external_image(order=order),
                    )
                )
                log_service_success(
                    self.logger_params,
                    operation="initialize_database",
                    message=f"Initialize {resource.name} Pokémons from external in database!",
                )
        await self.cache_service.set_cache(
            key=cache_key,
            data={"db_total": db_total, "external_total": external_total},
            ttl=86400,
        )

    async def find_one(
        self,
        param: str,
        **kwargs,
    ) -> Pokemon | None:
        user_request = kwargs.get("user_request") if kwargs else None
        try:
            pokemon = await self.repository.find_by(name=param)
            if pokemon is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, detail="Pokemon not found"
                )
            return await self._enrich_if_needed(pokemon)
        except Exception as exception:
            handle_service_exception(
                exception,
                logger=self.logger_params.logger,
                service=self.logger_params.service,
                operation="find_one",
                user_request=user_request,
                raise_exception=True,
            )
        finally:
            log_service_success(
                self.logger_params,
                operation="find_one",
                message=f"Find one {self.alias} successfully",
                user_request=user_request,
            )

    async def find_one_cached(
        self,
        param: str,
        **kwargs,
    ) -> Pokemon | None:
        clean_cache = kwargs.get("clean_cache") if kwargs else False
        key = self.cache_service.build_key_one(param=param)

        if clean_cache:
            await self.cache_service.delete_cache(cache_key=key)

        cached = await self.cache_service.get_one(key)
        if cached:
            if cached.model_dump().get("status") != PokemonStatusEnum.COMPLETE:
                cached = await self._enrich_if_needed(cached)
                await self.cache_service.set_one(key, cached)
            return cached
        item = await self.find_one(param, **kwargs)
        await self.cache_service.set_one(key, item)
        return item

    async def _enrich_if_needed(self, pokemon: Pokemon) -> Pokemon:
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
        pokemon.description = get_text_language(
            entries=species.get("flavor_text_entries"), title="flavor_text"
        ).text
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

        shape = await self.shape_service.sync_from_resource(species.get("shape"))
        pokemon.shape_id = shape.id if shape else None

        images = await self.image_service.sync_from_sprites(
            pokemon.order, payload.get("sprites")
        )
        pokemon.images_id = images.id if images else None

        habitat = await self.habitat_service.sync_from_resource(species.get("habitat"))
        pokemon.habitat_id = habitat.id if habitat else None

        growth_rate = await self.growth_rate_service.sync_from_resource(
            species.get("growth_rate")
        )
        pokemon.growth_rate_id = growth_rate.id if growth_rate else None

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
            await self.encounter_service.sync_from_resources(encounters)
        )

        evolutions = await self._sync_evolution_chain(pokemon)
        pokemon.evolutions = evolutions

        if (
            pokemon.growth_rate_id
            and pokemon.habitat_id
            and pokemon.shape_id
            and pokemon.images_id
        ):
            pokemon.status = PokemonStatusEnum.COMPLETE

        await self.repository.update(pokemon)

        return await self.repository.find_by(id=pokemon.id) or pokemon

    async def _sync_evolution_chain(self, pokemon: Pokemon) -> list[Pokemon]:
        if not pokemon.evolution_chain:
            return []
        chain_payload = (
            await self.client.get_evolution_chain_by_url(pokemon.evolution_chain)
        ).model_dump()
        names = collect_evolution_names(chain_payload.get("chain"))
        pokemons = await self.repository.list_by_names(names)
        return [candidate for candidate in pokemons if candidate.id != pokemon.id]
