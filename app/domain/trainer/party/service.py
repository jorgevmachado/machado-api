from __future__ import annotations

import logging
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.party.business import MAX_PARTY_SIZE

from app.domain.trainer.party.repository import TrainerPartyRepository
from app.domain.trainer.party.schema import (
    TrainerPartySchema,
)
from app.models import TrainerParty, OwnedPokemon
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)


class TrainerPartyService(BaseService[TrainerPartyRepository, TrainerParty]):
    def __init__(
        self,
        repository: TrainerPartyRepository,
    ) -> None:
        super().__init__(
            alias="TrainerParty",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="TrainerPartyService",
                operation="party",
            ),
            schema_class=TrainerPartySchema,
            cache_prefix="trainer_party",
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerPartyRepository(session))

    async def add(
        self,
        trainer_id: UUID,
        owned_pokemon: OwnedPokemon,
        is_active: bool = True,
        without_throw: bool = False,
    ) -> list[TrainerParty]:
        party_list: list[TrainerParty] = []
        entity_list = await self.repository.list_all(
            page_filter=FilterPage.build(trainer_id=trainer_id)
        )

        if isinstance(entity_list, list):
            party_list = entity_list
        else:
            party_list = entity_list.items

        entity = await self.repository.find_by(
            trainer_id=trainer_id, owned_pokemon_id=owned_pokemon.id
        )

        if entity:
            return entity_list

        if len(party_list) >= MAX_PARTY_SIZE:
            if without_throw:
                return party_list
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Trainer {trainer_id} already have {MAX_PARTY_SIZE} pokemon in party",
            )

        slot = len(party_list) + 1

        await self.repository.save(
            entity=TrainerParty(
                slot=slot,
                is_active=is_active,
                trainer_id=trainer_id,
                owned_pokemon_id=owned_pokemon.id,
            )
        )

        return await self.repository.list_all(
            page_filter=FilterPage.build(trainer_id=trainer_id)
        )

    async def get_or_create_list(
        self,
        trainer_id: UUID,
        party_slots: list[TrainerParty] | None = None,
        owned_pokemon: OwnedPokemon | None = None,
    ) -> list[TrainerParty]:
        if party_slots and len(party_slots) > 0:
            return party_slots

        exist_party_slot = await self.list_all(
            page_filter=FilterPage.build(trainer_id=trainer_id)
        )

        if exist_party_slot:
            return exist_party_slot

        if not owned_pokemon:
            return []

        return await self.add(
            trainer_id=trainer_id, owned_pokemon=owned_pokemon, without_throw=True
        )
