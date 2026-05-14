from __future__ import annotations

import logging
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import HTTPException, Query

from app.core.cache.service import CacheService
from app.core.logging import LoggingParams
from app.core.pagination import CustomLimitOffsetPage
from app.domain.pokedex.business import build_initial_pokedex_attributes
from app.domain.pokedex.repository import PokedexRepository
from app.domain.pokedex.schema import PokedexSchema
from app.models import Pokedex, User
from app.models.common import utcnow
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class PokedexService:
    def __init__(
        self,
        repository: PokedexRepository,
        trainer_service: TrainerService | None = None,
    ) -> None:
        self.repository = repository
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        logger_params = LoggingParams(
            logger=logger,
            service="PokedexService",
            operation="pokedex",
        )
        self.cache_service = CacheService(
            alias="Pokedex",
            prefix="pokedex",
            logger_params=logger_params,
            schema_class=PokedexSchema,
        )
        self.list_cache_service = CacheService(
            alias="PokedexList",
            prefix="pokedex",
            logger_params=logger_params,
            schema_class=PokedexSchema,
        )

    def _list_key(self, trainer_id: str, page_filter: FilterPage | None) -> str:
        filter_page = FilterPage.build(page_filter, trainer_id=trainer_id)
        return self.cache_service.cache.build_key(
            "pokedex", "list", filter_page.model_dump()
        )

    def _detail_key(self, trainer_id: str, pokemon_name: str) -> str:
        return self.cache_service.cache.build_key(
            "pokedex", "detail", trainer_id, pokemon_name
        )

    async def _invalidate_cache(
        self, trainer_id: str, pokemon_name: str | None = None
    ) -> None:
        await self.list_cache_service.delete_domain()
        if pokemon_name:
            await self.cache_service.cache.delete_cache(
                self._detail_key(trainer_id, pokemon_name)
            )

    async def _get_trainer_or_404(self, current_user: User):
        trainer = await self.trainer_service.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer not found",
            )
        return trainer

    async def list_all_cached(
        self,
        current_user: User,
        page_filter: Annotated[FilterPage, Query()] = None,
    ) -> list[PokedexSchema] | CustomLimitOffsetPage[PokedexSchema]:
        trainer = await self._get_trainer_or_404(current_user)
        clean_cache = page_filter.clean_cache if page_filter else False
        if clean_cache:
            await self.list_cache_service.delete_domain()
        if page_filter:
            page_filter.clean_cache = None

        key = self._list_key(str(trainer.id), page_filter)
        cached = await self.list_cache_service.get_list(key)
        if cached:
            return cached

        result = await self.repository.list_owned(trainer.id, page_filter)
        serialized = self._serialize_page_or_list(result)
        await self.list_cache_service.set_list(key, serialized)
        return serialized

    async def find_detail(self, current_user: User, pokemon_name: str) -> PokedexSchema:
        trainer = await self._get_trainer_or_404(current_user)
        key = self._detail_key(str(trainer.id), pokemon_name)
        cached = await self.cache_service.get_one(key)
        if cached:
            return cached

        entity = await self.repository.find_owned_detail(trainer.id, pokemon_name)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Pokedex entry not found",
            )
        serialized = self.to_schema(entity)
        await self.cache_service.set_one(key, serialized)
        return serialized

    async def discover(self, current_user: User, pokemon_name: str) -> PokedexSchema:
        trainer = await self._get_trainer_or_404(current_user)
        entity = await self.repository.find_owned_detail(trainer.id, pokemon_name)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Pokedex entry not found",
            )

        if not entity.discovered:
            await self.repository.mark_discovered(entity, discovered_at=utcnow())

        fresh = await self.repository.find_owned_detail(trainer.id, pokemon_name)
        if fresh is None:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Could not load discovered Pokedex entry",
            )
        await self._invalidate_cache(str(trainer.id), pokemon_name)
        return self.to_schema(fresh)

    async def initialize_for_trainer(
        self,
        *,
        trainer_id,
        discovered_pokemon_name: str,
        discovered_at: datetime | None = None,
        commit: bool = True,
    ) -> list[Pokedex]:
        pokemons = await self.repository.list_catalog_pokemon()
        attributes_by_pokemon_id = {
            pokemon.id: build_initial_pokedex_attributes(pokemon)
            for pokemon in pokemons
        }

        await self.repository.create_for_trainer(
            trainer_id=trainer_id,
            pokemons=pokemons,
            discovered_pokemon_name=discovered_pokemon_name,
            discovered_at=discovered_at,
            attributes_by_pokemon_id=attributes_by_pokemon_id,
        )

        if commit:
            await self.repository.session.commit()

        result: list[Pokedex] = []
        for pokemon in pokemons:
            entity = await self.repository.find_owned_detail(trainer_id, pokemon.name)
            if entity is not None:
                result.append(entity)

        if commit:
            await self._invalidate_cache(str(trainer_id), discovered_pokemon_name)
        return result

    def _serialize_page_or_list(self, result):
        if isinstance(result, CustomLimitOffsetPage):
            result.items = [self.to_schema(item) for item in result.items]
            return result
        return [self.to_schema(item) for item in result]

    @staticmethod
    def to_schema(entity: Pokedex) -> PokedexSchema:
        return PokedexSchema(
            id=entity.id,
            nickname=entity.nickname,
            level=entity.level,
            experience=entity.experience,
            hp=entity.hp,
            max_hp=entity.max_hp,
            attack=entity.attack,
            defense=entity.defense,
            special_attack=entity.special_attack,
            special_defense=entity.special_defense,
            speed=entity.speed,
            discovered=entity.discovered,
            discovered_at=entity.discovered_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            pokemon=entity.pokemon,
            trainer=entity.trainer,
        )
