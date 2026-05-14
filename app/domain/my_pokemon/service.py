from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated

from fastapi import HTTPException, Query

from app.core.cache.service import CacheService
from app.core.logging import LoggingParams
from app.core.pagination import CustomLimitOffsetPage
from app.domain.my_pokemon.business import (
    build_initial_attributes,
    build_unique_owned_name,
    resolve_effective_nickname,
    select_initial_moves,
    slugify_name,
)
from app.domain.my_pokemon.repository import MyPokemonRepository
from app.domain.my_pokemon.schema import (
    CreateMyPokemonSchema,
    MyPokemonOwnedMoveSchema,
    MyPokemonSchema,
)
from app.models import MyPokemon, User
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class MyPokemonService:
    def __init__(
        self,
        repository: MyPokemonRepository,
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
            service="MyPokemonService",
            operation="my_pokemon",
        )
        self.cache_service = CacheService(
            alias="MyPokemon",
            prefix="my_pokemon",
            logger_params=logger_params,
            schema_class=MyPokemonSchema,
        )
        self.list_cache_service = CacheService(
            alias="MyPokemonList",
            prefix="my_pokemon",
            logger_params=logger_params,
            schema_class=MyPokemonSchema,
        )

    def _list_key(self, trainer_id: str, page_filter: FilterPage | None) -> str:
        filter_page = FilterPage.build(page_filter, trainer_id=trainer_id)
        return self.cache_service.cache.build_key(
            "my_pokemon", "list", filter_page.model_dump()
        )

    def _detail_key(self, trainer_id: str, name: str) -> str:
        return self.cache_service.cache.build_key(
            "my_pokemon", "detail", trainer_id, name
        )

    async def _invalidate_cache(self, trainer_id: str, name: str | None = None) -> None:
        await self.list_cache_service.delete_domain()
        if name:
            await self.cache_service.cache.delete_cache(
                self._detail_key(trainer_id, name)
            )

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

    async def list_all_cached(
        self,
        current_user: User,
        page_filter: Annotated[FilterPage, Query()] = None,
    ) -> list[MyPokemonSchema] | CustomLimitOffsetPage[MyPokemonSchema]:
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

    async def find_detail(self, current_user: User, name: str) -> MyPokemonSchema:
        trainer = await self._get_trainer_or_404(current_user)
        key = self._detail_key(str(trainer.id), name)
        cached = await self.cache_service.get_one(key)
        if cached:
            return cached

        entity = await self.repository.find_owned_detail(trainer.id, name)
        if entity is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="My Pokemon not found",
            )
        serialized = self.to_schema(entity)
        await self.cache_service.set_one(key, serialized)
        return serialized

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
            fresh = await self.repository.find_owned_detail(trainer_id, public_name)
            if fresh is None:
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Could not load created My Pokemon",
                )
            await self._invalidate_cache(str(trainer_id), public_name)
            return fresh
        except Exception:
            if commit:
                await self.repository.session.rollback()
            raise

    def _serialize_page_or_list(self, result):
        if isinstance(result, CustomLimitOffsetPage):
            result.items = [self.to_schema(item) for item in result.items]
            return result
        return [self.to_schema(item) for item in result]

    def to_schema(self, entity: MyPokemon) -> MyPokemonSchema:
        return MyPokemonSchema(
            id=entity.id,
            name=entity.name,
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
            captured_at=entity.captured_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            pokemon=entity.pokemon,
            trainer=entity.trainer,
            moves=[
                MyPokemonOwnedMoveSchema(
                    id=move.id,
                    pp=move.pp,
                    max_pp=move.max_pp,
                    pokemon_move_id=move.pokemon_move_id,
                    pokemon_move_name=move.pokemon_move.name,
                    pokemon_move_type=move.pokemon_move.type,
                    pokemon_move_power=move.pokemon_move.power,
                    pokemon_move_accuracy=move.pokemon_move.accuracy,
                )
                for move in entity.moves
                if move.deleted_at is None and move.pokemon_move is not None
            ],
        )
