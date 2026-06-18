from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.owned_pokemon.move.business import select_initial_moves

from app.domain.trainer.owned_pokemon.move.repository import OwnedPokemonMoveRepository
from app.domain.trainer.owned_pokemon.move.schema import (
    OwnedPokemonMoveSchema,
)
from app.models import Move, OwnedPokemonMove

logger = logging.getLogger(__name__)


class OwnedPokemonMoveService(
    BaseService[OwnedPokemonMoveRepository, OwnedPokemonMove]
):
    def __init__(
        self,
        repository: OwnedPokemonMoveRepository,
    ) -> None:
        super().__init__(
            alias="Move",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="OwnedPokemonMoveService",
                operation="trainer.owned_pokemon.move",
            ),
            schema_class=OwnedPokemonMoveSchema,
            cache_prefix="move",
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(OwnedPokemonMoveRepository(session))

    async def sync_form_resources(
        self, owned_pokemon_id: UUID, resources: list[Move]
    ) -> list[OwnedPokemonMove]:
        selected_moves = select_initial_moves(moves=resources)
        synced: list[OwnedPokemonMove] = []
        for entry in selected_moves:
            synced.append(
                await self.get_or_create(
                    resource=entry, owned_pokemon_id=owned_pokemon_id
                )
            )
        return synced

    async def get_or_create(
        self, resource: Move, owned_pokemon_id: UUID
    ) -> OwnedPokemonMove:
        entity = await self.repository.find_by(
            owned_pokemon_id=owned_pokemon_id,
            pokemon_move_id=resource.id,
        )
        if entity:
            return entity

        return await self.repository.save(
            entity=OwnedPokemonMove(
                pp=resource.pp,
                max_pp=resource.pp,
                pokemon_move_id=resource.id,
                owned_pokemon_id=owned_pokemon_id,
            ),
        )
