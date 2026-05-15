from __future__ import annotations

import logging
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.core.logging import LoggingParams
from app.core.pagination import CustomLimitOffsetPage
from app.core.service import BaseService
from app.domain.trainer.pokedex.business import build_initial_pokedex_attributes
from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.models import Pokedex, User, Trainer
from app.models.common import utcnow

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class PokedexService(BaseService[PokedexRepository, Pokedex]):
    def __init__(
        self,
        repository: PokedexRepository,
        trainer_service: TrainerService | None = None,
    ) -> None:
        super().__init__(
            alias="Pokedex",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokedexService", operation="pokedex"
            ),
            schema_class=PokedexSchema,
            cache_prefix="pokedex",
        )
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        self.list_cache_service = self.cache_service

    async def _get_trainer_or_404(self, current_user: User):
        trainer = await self.trainer_service.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer not found",
            )
        return trainer

    async def _resolve_trainer(self, trainer_or_user: Trainer | User) -> Trainer:
        if hasattr(trainer_or_user, "user_id") and hasattr(
            trainer_or_user, "capture_rate"
        ):
            return trainer_or_user
        return await self._get_trainer_or_404(trainer_or_user)

    async def list_all_cached(self, page_filter=None, user_request=None, trainer_id=None):
        if trainer_id is None and page_filter is not None and not hasattr(
            page_filter, "model_dump"
        ):
            trainer = await self._resolve_trainer(page_filter)
            resolved_page_filter = (
                user_request if hasattr(user_request, "model_dump") else None
            )
            resolved_user_request = (
                None if resolved_page_filter is not None else user_request
            )
            return await super().list_all_cached(
                page_filter=resolved_page_filter,
                user_request=resolved_user_request,
                trainer_id=str(trainer.id),
            )
        return await super().list_all_cached(
            page_filter=page_filter,
            user_request=user_request,
            trainer_id=trainer_id,
        )

    async def discover(self, trainer: Trainer | User, pokemon_name: str) -> PokedexSchema:
        trainer = await self._resolve_trainer(trainer)
        entity = await self.repository.find_by(
            trainer_id=trainer.id,
            name=pokemon_name,
        )
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Pokedex entry not found",
            )

        if not entity.discovered:
            await self.repository.mark_discovered(entity, discovered_at=utcnow())

        fresh = await self.repository.find_by(
            trainer_id=trainer.id,
            name=pokemon_name,
        )
        if fresh is None:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Could not load discovered Pokedex entry",
            )
        await self._invalidate_cache(
            trainer_id=str(trainer.id),
            identifier=str(entity.id)
        )
        return self.to_schema(fresh)

    async def find_detail(self, trainer: Trainer, name: str) -> PokedexSchema:
        trainer = await self._resolve_trainer(trainer)
        return await self.find_one_cached(param=name, trainer_id=str(trainer.id))

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
            entity = await self.repository.find_by(
                trainer_id=trainer_id,
                name=pokemon.name,
            )
            if entity is not None:
                result.append(entity)

        if commit:
            await self._invalidate_cache(
                identifier=discovered_pokemon_name,
                trainer_id=str(trainer_id),
            )
        return result

    @staticmethod
    def to_schema(entity: Pokedex) -> PokedexSchema:
        return PokedexSchema.model_validate(entity)

    def _serialize_page_or_list(self, result):
        if isinstance(result, CustomLimitOffsetPage):
            result.items = [self.to_schema(item) for item in result.items]
            return result
        return [self.to_schema(item) for item in result]
