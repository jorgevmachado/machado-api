from __future__ import annotations

import logging
from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.pagination import CustomLimitOffsetPage
from app.core.service.base import BaseService
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.pokedex.pokedex_entry.service import PokedexEntryService

from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.pokedex.schema import (
    PokedexSchema,
)
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    Pokedex,
    Pokemon,
    PokedexEntry,
    Trainer,
    TrainerLogEventEnum,
    LogTypeEnum,
)
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)


class PokedexService(BaseService[PokedexRepository, Pokedex]):
    def __init__(
        self,
        repository: PokedexRepository,
        pokemon_service: PokemonService | None = None,
        pokedex_entry_service: PokedexEntryService | None = None,
        trainer_log: TrainerLogService | None = None,
    ) -> None:
        super().__init__(
            alias="Pokedex",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="PokedexService",
                operation="trainer.pokedex",
            ),
            schema_class=PokedexSchema,
            cache_prefix="pokedex",
        )
        session = repository.session
        self.pokemon_service = pokemon_service or PokemonService.from_session(session)
        self.pokedex_entry_service = (
            pokedex_entry_service or PokedexEntryService.from_session(session)
        )
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(PokedexRepository(session))

    async def create(
        self,
        trainer_id: UUID,
        discovered_pokemon: Pokemon | None = None,
        discovered_at: datetime | None = None,
        commit: bool = True,
    ) -> Pokedex:
        try:
            pokedex = Pokedex(trainer_id=trainer_id)
            self.repository.session.add(pokedex)
            await self.repository.session.flush()

            pokemon_list: list[Pokemon] = []
            pokemons = await self.pokemon_service.list_all()
            if isinstance(pokemons, list):
                pokemon_list = pokemons

            await self.pokedex_entry_service.sync_from_resources(
                pokedex_id=pokedex.id,
                resources=pokemon_list,
                discovered_at=discovered_at,
                discovered_pokemon=discovered_pokemon,
            )

            if commit:
                await self.repository.session.commit()
                await self.repository.session.refresh(pokedex)

            fresh = await self.repository.find_by(trainer_id=trainer_id)

            if fresh is None:
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Could not load created Pokedex",
                )

            if commit:
                await self.cache_service.delete_domain()

            return fresh
        except Exception:
            if commit:
                await self.repository.session.rollback()
            raise

    async def get_by(
        self, trainer_id: str | None = None, clean_cache: bool | None = False
    ) -> str:
        if not trainer_id:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer ID is required to fetch Pokedex",
            )

        key = self.cache_service.build_key_one(param=str(trainer_id))
        if clean_cache:
            await self.cache_service.delete_cache(cache_key=key)

        cached = await self.cache_service.cache.get_cache(key=key)
        if cached:
            return cached.get("id")

        pokedex = await self.repository.find_by(trainer_id=trainer_id)

        if not pokedex:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Pokedex not found for the given trainer ID",
            )
        pokedex_id = str(pokedex.id)
        await self.cache_service.set_cache(
            key=key,
            data={"id": pokedex_id},
        )

        return pokedex_id

    async def list_all_cached(
        self,
        page_filter: Annotated[FilterPage, Query()] = None,
        user_request: str | None = None,
        **kwargs,
    ) -> list[PokedexEntry] | CustomLimitOffsetPage[PokedexEntry] | None:
        pokedex_id = await self.get_by(
            trainer_id=page_filter.trainer_id, clean_cache=page_filter.clean_cache
        )
        filter_page = FilterPage.build(page_filter, pokedex_id=pokedex_id)
        return await self.pokedex_entry_service.list_all_cached(
            page_filter=filter_page, user_request=user_request
        )

    async def find_one_cached(
        self,
        param: str,
        **kwargs,
    ) -> PokedexEntry:
        pokedex_id = await self.get_by(
            trainer_id=kwargs.get("trainer_id"), clean_cache=kwargs.get("clean_cache")
        )
        return await self.pokedex_entry_service.find_one_cached(
            param=param,
            pokedex_id=pokedex_id,
            clean_cache=kwargs.get("clean_cache"),
            user_request=kwargs.get("user_request"),
        )

    async def get_or_create(
        self,
        trainer: Trainer,
        commit: bool = True,
        discovered_at: datetime | None = None,
        discovered_pokemon: Pokemon | None = None,
    ) -> Pokedex:
        if trainer.pokedex:
            return trainer.pokedex

        exist_pokedex = await self.find_by(trainer_id=trainer.id, without_throw=True)

        if exist_pokedex:
            return exist_pokedex

        created_pokedex = await self.create(
            commit=commit,
            trainer_id=trainer.id,
            discovered_at=discovered_at,
            discovered_pokemon=discovered_pokemon,
        )

        await self.trainer_log.create(
            event=TrainerLogEventEnum.CREATED,
            user_id=trainer.user_id,
            pokedex=created_pokedex,
            log_type=LogTypeEnum.POKEDEX,
            trainer_id=trainer.id,
        )

        return created_pokedex

    async def discover(
        self, trainer: Trainer, name: str, without_throw: bool = False
    ) -> PokedexEntry:
        pokedex_id = await self.get_by(trainer_id=str(trainer.id))

        return await self.pokedex_entry_service.discover(
            name=name,
            trainer=trainer,
            pokedex_id=pokedex_id,
            without_throw=without_throw,
        )
