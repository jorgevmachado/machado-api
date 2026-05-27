from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Annotated

from fastapi import HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.service import CacheService
from app.core.exceptions import handle_service_exception
from app.core.logging import LoggingParams
from app.core.pagination import CustomLimitOffsetPage
from app.core.service.base import BaseService

from app.domain.pokemon.ability.service import AbilityService
from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.schema import (
    PokemonSchema,
)

from app.domain.pokemon.encounter.service import EncounterService
from app.domain.pokemon.growth_rate.service import GrowthRateService
from app.domain.pokemon.habitat.service import HabitatService
from app.domain.pokemon.image.service import ImageService
from app.domain.pokemon.move.service import MoveService
from app.domain.pokemon.shape.service import ShapeService
from app.domain.pokemon.type.service import TypeService
from app.infrastructure.external_api import PokeApiClient
from app.models import Pokemon

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
        self.list_cache_service = CacheService(
            alias="PokemonList",
            prefix="pokemon",
            logger_params=LoggingParams(
                logger=logger, service="PokemonService", operation="pokemon_list"
            ),
            schema_class=PokemonSchema,
        )
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
            growth_rate_service
            or GrowthRateService.from_session(session, self.client)
        )
        self.habitat_service = habitat_service or HabitatService.from_session(
            session, self.client
        )
        self.shape_service = shape_service or ShapeService.from_session(
            session, self.client
        )
        self.encounter_service = (
            encounter_service
            or EncounterService.from_session(session, self.client)
        )