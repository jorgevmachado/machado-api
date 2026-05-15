from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.core.logging import LoggingParams
from app.core.pagination import CustomLimitOffsetPage
from app.core.service import BaseService
from app.domain.trainer.my_pokemon.business import (
    build_unique_owned_name,
    resolve_effective_nickname,
    select_initial_moves,
    slugify_name,
)
from app.domain.trainer.progression.business import build_initial_attributes
from app.domain.trainer.my_pokemon.repository import MyPokemonRepository
from app.domain.trainer.my_pokemon.schema import (
    CreateMyPokemonSchema,
    MyPokemonSchema,
)
from app.models import MyPokemon, User

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class MyPokemonService(BaseService[MyPokemonRepository, MyPokemon]):
    def __init__(
        self,
        repository: MyPokemonRepository,
        trainer_service: TrainerService | None = None,
    ) -> None:
        super().__init__(
            alias="MyPokemon",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="MyPokemonService",
                operation="my_pokemon",
            ),
            schema_class=MyPokemonSchema,
            cache_prefix="my_pokemon",
        )
        session = repository.session
        if trainer_service is None:
            from app.domain.trainer.service import TrainerService

            trainer_service = TrainerService.from_session(session)
        self.trainer_service = trainer_service
        self.list_cache_service = self.cache_service

    async def create(
        self,
        current_user: User,
        payload: CreateMyPokemonSchema,
    ) -> MyPokemonSchema:
        trainer = await self.trainer_service.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Trainer not initialized",
            )
        created = await self.create_owned_for_trainer(
            trainer_id=trainer.id,
            pokemon_name=payload.pokemon_name,
            nickname=payload.nickname,
        )
        return self.to_schema(created)

    async def list_all_cached(self, current_user: User, page_filter=None):
        trainer = await self._get_trainer_or_404(current_user)
        return await super().list_all_cached(
            page_filter=page_filter,
            trainer_id=str(trainer.id),
        )

    async def find_detail(self, current_user: User, name: str) -> MyPokemonSchema:
        trainer = await self._get_trainer_or_404(current_user)
        return await super().find_one_cached(param=name, trainer_id=str(trainer.id))

    async def _get_trainer_or_404(self, current_user: User):
        trainer = await self.trainer_service.get_by_user_id(current_user.id)
        if trainer is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Trainer not found",
            )
        return trainer

    async def create_owned_for_trainer(
        self,
        *,
        trainer_id,
        pokemon_name: str,
        nickname: str | None,
        commit: bool = True,
    ) -> MyPokemon:
        try:
            base_pokemon = await self.repository.find_base_pokemon(
                pokemon_name.strip().lower()
            )
            if base_pokemon is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Pokemon not found",
                )

            effective_nickname = resolve_effective_nickname(base_pokemon.name, nickname)
            existing_names = await self.repository.list_existing_owned_names(trainer_id)
            public_name = build_unique_owned_name(
                slugify_name(effective_nickname),
                existing_names,
            )
            attributes = build_initial_attributes(base_pokemon)
            owned = await self.repository.create_owned(
                trainer_id=trainer_id,
                pokemon_id=base_pokemon.id,
                name=public_name,
                nickname=effective_nickname,
                attributes=attributes,
            )
            selected_moves = select_initial_moves(list(base_pokemon.moves))
            await self.repository.attach_moves(
                my_pokemon_id=owned.id,
                moves=selected_moves,
            )
            if commit:
                await self.repository.session.commit()
            await self.repository.session.refresh(owned)
            fresh = await self.repository.find_by(
                trainer_id=trainer_id,
                name=public_name,
            )
            if fresh is None:
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Could not load created My Pokemon",
                )
            await self._invalidate_cache(
                trainer_id=str(trainer_id),
                identifier=public_name,
            )
            return fresh
        except Exception:
            if commit:
                await self.repository.session.rollback()
            raise

    @staticmethod
    def to_schema(entity: MyPokemon) -> MyPokemonSchema:
        return MyPokemonSchema.model_validate(entity)

    def _serialize_page_or_list(self, result):
        if isinstance(result, CustomLimitOffsetPage):
            result.items = [self.to_schema(item) for item in result.items]
            return result
        return [self.to_schema(item) for item in result]
