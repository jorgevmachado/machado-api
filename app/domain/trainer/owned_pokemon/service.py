from __future__ import annotations

import logging
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.service import PokemonService
from app.domain.trainer.owned_pokemon.business import (
    resolve_effective_nickname,
    slugify_name,
    build_unique_owned_name,
)
from app.domain.trainer.owned_pokemon.move.service import OwnedPokemonMoveService

from app.domain.trainer.owned_pokemon.repository import OwnedPokemonRepository
from app.domain.trainer.owned_pokemon.schema import (
    OwnedPokemonSchema,
)
from app.domain.trainer.progression import build_initial_attributes
from app.models import OwnedPokemon, Pokemon
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)


class OwnedPokemonService(BaseService[OwnedPokemonRepository, OwnedPokemon]):
    def __init__(
        self,
        repository: OwnedPokemonRepository,
        pokemon_service: PokemonService | None = None,
        owned_pokemon_move_service: OwnedPokemonMoveService | None = None,
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

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(OwnedPokemonRepository(session))

    async def create(
        self,
        trainer_id: UUID,
        pokemon: Pokemon,
        nickname: str | None,
        commit: bool = True,
    ) -> OwnedPokemon:
        try:
            effective_nickname = resolve_effective_nickname(pokemon.name, nickname)
            existing_pokemons = await self.list_all(
                page_filter=FilterPage.build(trainer_id=trainer_id)
            )

            public_name = build_unique_owned_name(
                slugify_name(effective_nickname),
                existing_pokemons,
            )

            attributes = build_initial_attributes(pokemon)

            owned_pokemon = OwnedPokemon(
                name=public_name,
                nickname=effective_nickname,
                trainer_id=trainer_id,
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
                trainer_id=trainer_id, name=public_name
            )

            if fresh is None:
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Could not load created Owned Pokemon",
                )

            if commit:
                await self.cache_service.delete_domain()

            return fresh
        except Exception:
            if commit:
                await self.repository.session.rollback()
            raise
