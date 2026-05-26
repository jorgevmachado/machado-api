from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.my_pokemon.business import (
    build_unique_owned_name,
    resolve_effective_nickname,
    slugify_name,
)
from app.domain.trainer.my_pokemon.move import MyPokemonMoveService
from app.domain.trainer.my_pokemon.repository import MyPokemonRepository
from app.domain.trainer.my_pokemon.schema import (
    CreateMyPokemonSchema,
    MyPokemonSchema,
)
from app.domain.trainer.progression.business import build_initial_attributes
from app.models import MyPokemon, Trainer
from app.models.common import utcnow
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.trainer.service import TrainerService


class MyPokemonService(BaseService[MyPokemonRepository, MyPokemon]):
    def __init__(
            self,
            repository: MyPokemonRepository,
            trainer_service: TrainerService | None = None,
            pokemon_service: PokemonService | None = None,
            my_pokemon_move_service: MyPokemonMoveService | None = None,
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
        if pokemon_service is None:
            from app.domain.pokemon.service import PokemonService

            pokemon_service = PokemonService.from_session(session)
        self.pokemon_service = pokemon_service
        if my_pokemon_move_service is None:
            from app.domain.trainer.my_pokemon.move.service import MyPokemonMoveService

            my_pokemon_move_service = MyPokemonMoveService.from_session(session)
        self.my_pokemon_move_service = my_pokemon_move_service
        self.list_cache_service = self.cache_service

    @classmethod
    def from_session(cls, session: AsyncSession) -> "MyPokemonService":
        return cls(MyPokemonRepository(session))

    @staticmethod
    def apply_full_healing(entity: MyPokemon) -> dict[str, int | bool]:
        healed_at = utcnow()
        restored_hp = max(entity.max_hp - entity.hp, 0)
        restored_pp = 0
        was_revived = entity.hp == 0 and entity.max_hp > 0

        if restored_hp > 0:
            entity.hp = entity.max_hp
            entity.updated_at = healed_at

        for move in entity.moves:
            if move.deleted_at is not None:
                continue
            restored_move_pp = max(move.max_pp - move.pp, 0)
            if restored_move_pp <= 0:
                continue
            move.pp = move.max_pp
            move.updated_at = healed_at
            restored_pp += restored_move_pp

        return {
            "restored_hp": restored_hp,
            "restored_pp": restored_pp,
            "was_revived": was_revived,
            "changed": restored_hp > 0 or restored_pp > 0,
        }

    async def create(
            self,
            trainer: Trainer,
            payload: CreateMyPokemonSchema,
    ) -> MyPokemon:
        return await self.create_owned_for_trainer(
            trainer_id=trainer.id,
            pokemon_name=payload.pokemon_name,
            nickname=payload.nickname,
        )

    async def create_owned_for_trainer(
            self,
            *,
            trainer_id,
            pokemon_name: str,
            nickname: str | None,
            commit: bool = True,
    ) -> MyPokemon:
        try:
            base_pokemon = await self.pokemon_service.find_detail(
                identifier=pokemon_name.strip().lower()
            )
            if base_pokemon is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Pokemon not found",
                )

            effective_nickname = resolve_effective_nickname(base_pokemon.name, nickname)
            existing_names = await self.list_all(page_filter=FilterPage.build(trainer_id=trainer_id))
            public_name = build_unique_owned_name(
                slugify_name(effective_nickname),
                existing_names,
            )
            attributes = build_initial_attributes(base_pokemon)
            owned = MyPokemon(
                trainer_id=trainer_id,
                pokemon_id=base_pokemon.id,
                name=public_name,
                nickname=effective_nickname,
                **attributes,
            )
            self.repository.session.add(owned)
            await self.repository.session.flush()

            await self.my_pokemon_move_service.sync_from_resources(
                my_pokemon_id=owned.id,
                resources=list(base_pokemon.moves)
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
            if commit:
                await self._invalidate_cache(
                    trainer_id=str(trainer_id),
                    identifier=public_name,
                )
            return fresh
        except Exception:
            if commit:
                await self.repository.session.rollback()
            raise
