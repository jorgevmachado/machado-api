from __future__ import annotations
from uuid import UUID

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service import BaseService
from app.domain.trainer.my_pokemon.move import select_initial_moves
from app.domain.trainer.my_pokemon.move.repository import MyPokemonMoveRepository
from app.domain.trainer.my_pokemon.schema import (
    MyPokemonSchema,
)
from app.models import MyPokemonMove, PokemonMove

logger = logging.getLogger(__name__)


class MyPokemonMoveService(BaseService[MyPokemonMoveRepository, MyPokemonMove]):
    def __init__(
            self,
            repository: MyPokemonMoveRepository,
    ) -> None:
        super().__init__(
            alias="MyPokemonMove",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="MyPokemonMoveService",
                operation="my_pokemon_move",
            ),
            schema_class=MyPokemonSchema,
            cache_prefix="my_pokemon_move",
        )
        self.list_cache_service = self.cache_service

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(MyPokemonMoveRepository(session))

    async def sync_from_resources(self, my_pokemon_id: UUID, resources: list[PokemonMove]) -> list[ MyPokemonMove]:
        selected_moves = select_initial_moves(resources)
        synced: list[MyPokemonMove] = []
        for entry in selected_moves:
            synced.append(
                await self.get_or_create(
                    pp=entry.pp,
                    max_pp=entry.pp,
                    my_pokemon_id=my_pokemon_id,
                    pokemon_move_id=entry.id,
                )
            )
        return synced

    async def get_or_create(self, pp: int, max_pp: int, my_pokemon_id: UUID, pokemon_move_id: UUID) -> MyPokemonMove:
        entity = await self.repository.find_by(
            my_pokemon_id=my_pokemon_id,
            pokemon_move_id=pokemon_move_id,
        )
        if entity:
            return entity

        return await self.repository.save(
            entity=MyPokemonMove(
                pp=pp,
                max_pp=max_pp,
                my_pokemon_id=my_pokemon_id,
                pokemon_move_id=pokemon_move_id,
            ),
        )