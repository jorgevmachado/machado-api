from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.owned_pokemon.business import (
    resolve_effective_nickname,
    slugify_name,
    build_unique_owned_name,
    calculate_capture_chance_percent,
    rolled_capture_success,
)
from app.domain.trainer.owned_pokemon.move.service import OwnedPokemonMoveService

from app.domain.trainer.owned_pokemon.repository import OwnedPokemonRepository
from app.domain.trainer.owned_pokemon.schema import (
    OwnedPokemonSchema,
)
from app.domain.trainer.progression import build_initial_attributes
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    OwnedPokemon,
    TrainerLogEventEnum,
    LogTypeEnum,
    Trainer,
    LogStatusEnum, Pokemon,
)
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)


class OwnedPokemonService(BaseService[OwnedPokemonRepository, OwnedPokemon]):
    def __init__(
        self,
        repository: OwnedPokemonRepository,
        pokemon_service: PokemonService | None = None,
        owned_pokemon_move_service: OwnedPokemonMoveService | None = None,
        trainer_log: TrainerLogService | None = None,
    ) -> None:
        super().__init__(
            alias="OwnedPokemon",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="OwnedPokemonService",
                operation="trainer.owned_pokemon",
            ),
            schema_class=OwnedPokemonSchema,
            cache_prefix="owned_pokemon",
        )
        session = repository.session
        self.pokemon_service = pokemon_service or PokemonService.from_session(session)
        self.owned_pokemon_move_service = (
            owned_pokemon_move_service or OwnedPokemonMoveService.from_session(session)
        )
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(OwnedPokemonRepository(session))

    async def create(
        self,
        trainer: Trainer,
        pokemon_name: str,
        nickname: str | None,
        commit: bool = True,
        pokedex_hp: int | None = None,
        pokedex_max_hp: int | None = None,
        only_allowed_pokemon: list[str] | None = None,
        trainer_capture_rate: int | None = None,
    ) -> OwnedPokemon:
        try:
            pokemon_name = pokemon_name.strip().lower()
            if only_allowed_pokemon and pokemon_name not in only_allowed_pokemon:
                message = f"Pokemon {pokemon_name} is not allowed"
                await self.trainer_log.create(
                    event=TrainerLogEventEnum.CAPTURED,
                    user_id=trainer.user.id,
                    message=message,
                    log_type=LogTypeEnum.POKEMON,
                    trainer_id=trainer.id,
                )
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail=message,
                )

            pokemon = await self.pokemon_service.find_one(param=pokemon_name)

            if not pokemon:
                message = f"Pokemon {pokemon_name} not found"
                await self.trainer_log.create(
                    event=TrainerLogEventEnum.CAPTURED,
                    user_id=trainer.user.id,
                    status=LogStatusEnum.ERROR,
                    message=message,
                    log_type=LogTypeEnum.POKEMON,
                    trainer_id=trainer.id,
                )
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=message,
                )
            
            await self.validate_capture_rate(
                trainer=trainer,
                pokemon=pokemon,
                pokedex_hp=pokedex_hp,
                pokedex_max_hp=pokedex_max_hp,
                trainer_capture_rate=trainer_capture_rate,
            )

            effective_nickname = resolve_effective_nickname(pokemon.name, nickname)
            existing_pokemons = await self.list_all(
                page_filter=FilterPage.build(trainer_id=trainer.id)
            )

            public_name = build_unique_owned_name(
                slugify_name(effective_nickname),
                existing_pokemons,
            )

            attributes = build_initial_attributes(pokemon)

            owned_pokemon = OwnedPokemon(
                name=public_name,
                nickname=effective_nickname,
                trainer_id=trainer.id,
                pokemon_id=pokemon.id,
                **attributes,
            )

            self.repository.session.add(owned_pokemon)
            await self.repository.session.flush()

            await self.owned_pokemon_move_service.sync_form_resources(
                owned_pokemon_id=owned_pokemon.id,
                resources=pokemon.moves,
            )

            if commit:
                await self.repository.session.commit()
                await self.repository.session.refresh(owned_pokemon)

            fresh = await self.repository.find_by(
                trainer_id=trainer.id, name=public_name
            )

            if fresh is None:
                message = f"Could not load created Owned Pokemon with name {public_name} for trainer {trainer.user.username}"
                await self.trainer_log.create(
                    event=TrainerLogEventEnum.CAPTURED,
                    user_id=trainer.user.id,
                    status=LogStatusEnum.ERROR,
                    message=message,
                    log_type=LogTypeEnum.POKEMON,
                    trainer_id=trainer.id,
                )
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail=message,
                )

            if commit:
                await self.cache_service.delete_domain()

            return fresh
        except Exception:
            if commit:
                await self.repository.session.rollback()
            raise

    async def get_or_create(
        self,
        trainer: Trainer,
        pokemon_name: str,
        commit: bool = True,
        nickname: str | None = None,
        owned_pokemons: list[OwnedPokemon] | None = None,
        only_allowed_pokemon: list[str] | None = None,
    ) -> OwnedPokemon:
        owned_pokemon = (
            owned_pokemons[0] if owned_pokemons and len(owned_pokemons) > 0 else None
        )

        if owned_pokemon:
            return owned_pokemon

        exist_owned_pokemon = await self.find_by(
            trainer_id=trainer.id, pokemon_name=pokemon_name, without_throw=True
        )

        if exist_owned_pokemon:
            return exist_owned_pokemon

        await self.pokemon_service.list_all_cached(
            page_filter=FilterPage.build(page=1, limit=1)
        )
        
        crated_owned_pokemon = await self.create(
            commit=commit,
            trainer=trainer,
            nickname=nickname,
            pokemon_name=pokemon_name,
            only_allowed_pokemon=only_allowed_pokemon,
        )

        
        
        return crated_owned_pokemon


    async def validate_capture_rate(
            self,
            trainer: Trainer,
            pokemon: Pokemon,
            pokedex_hp: int | None,
            pokedex_max_hp: int | None,
            trainer_capture_rate: int | None
    ) -> None:

        if not trainer_capture_rate or not pokedex_hp or not pokedex_max_hp:
            return

        if trainer_capture_rate < pokemon.capture_rate:
            message = f"Pokemon {pokemon.name} has a capture rate of {pokemon.capture_rate} which is higher than the trainer's capture rate of {trainer_capture_rate}"

            await self.trainer_log.create(
                event=TrainerLogEventEnum.CAPTURED,
                user_id=trainer.user.id,
                status=LogStatusEnum.ERROR,
                message=message,
                log_type=LogTypeEnum.POKEMON,
                trainer_id=trainer.id,
            )
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail= message,
            )

        capture_chance_percent = calculate_capture_chance_percent(
            pokedex_hp=pokedex_hp,
            pokedex_max_hp=pokedex_max_hp,
            trainer_capture_rate=trainer_capture_rate,
            pokemon_capture_rate=pokemon.capture_rate or 0,
        )

        capture_chance = rolled_capture_success(capture_chance_percent)

        if not capture_chance:
            message = f"Pokemon {pokemon.name} has a capture rate of {pokemon.capture_rate} which is higher than the trainer's capture rate of {trainer_capture_rate}"
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CAPTURED,
                user_id=trainer.user.id,
                status=LogStatusEnum.ERROR,
                message=message,
                log_type=LogTypeEnum.POKEMON,
                trainer_id=trainer.id,
            )
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=message,
            )