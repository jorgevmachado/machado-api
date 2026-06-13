from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.party.business import MAX_PARTY_SIZE

from app.domain.trainer.party.repository import TrainerPartyRepository
from app.domain.trainer.party.schema import (
    TrainerPartySchema,
)
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    TrainerParty,
    OwnedPokemon,
    Trainer,
    TrainerLogEventEnum,
    LogTypeEnum,
    LogStatusEnum,
)
from app.shared.schemas import FilterPage

logger = logging.getLogger(__name__)


class TrainerPartyService(BaseService[TrainerPartyRepository, TrainerParty]):
    def __init__(
        self,
        repository: TrainerPartyRepository,
        trainer_log: TrainerLogService | None = None,
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
        session = repository.session
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(TrainerPartyRepository(session))

    async def add(
        self,
        trainer: Trainer,
        owned_pokemon: OwnedPokemon,
        is_active: bool = True,
        without_throw: bool = False,
    ) -> list[TrainerParty]:
        party_list: list[TrainerParty] = []
        entity_list = await self.repository.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id)
        )

        if isinstance(entity_list, list):
            party_list = entity_list
        else:
            party_list = entity_list.items

        entity = await self.repository.find_by(
            trainer_id=trainer.id, owned_pokemon_id=owned_pokemon.id
        )

        if entity:
            return entity_list

        if len(party_list) >= MAX_PARTY_SIZE:
            message = (
                f"Trainer {trainer.id} already have {MAX_PARTY_SIZE} pokemon in party"
            )
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CREATED,
                user_id=trainer.user.id,
                log_type=LogTypeEnum.PARTY,
                status=LogStatusEnum.ERROR,
                trainer_id=trainer.id,
                message=message,
            )
            if without_throw:
                return party_list
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=message,
            )

        slot = len(party_list) + 1

        created_trainer_party = await self.repository.save(
            entity=TrainerParty(
                slot=slot,
                is_active=is_active,
                trainer_id=trainer.id,
                owned_pokemon_id=owned_pokemon.id,
            )
        )

        await self.trainer_log.create(
            event=TrainerLogEventEnum.CREATED,
            user_id=trainer.user.id,
            log_type=LogTypeEnum.PARTY,
            trainer_id=trainer.id,
            trainer_parties=[created_trainer_party],
        )

        return await self.repository.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id)
        )

    async def get_or_create_list(
        self,
        trainer: Trainer,
        owned_pokemon: OwnedPokemon | None = None,
    ) -> list[TrainerParty]:
        party_slots = trainer.party_slots
        if party_slots and len(party_slots) > 0:
            return party_slots

        exist_party_slot = await self.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id)
        )

        if exist_party_slot:
            return exist_party_slot

        if not owned_pokemon:
            await self.trainer_log.create(
                event=TrainerLogEventEnum.CREATED,
                user_id=trainer.user.id,
                log_type=LogTypeEnum.PARTY,
                status=LogStatusEnum.ERROR,
                trainer_id=trainer.id,
                message="Could not load owned Pokemon",
            )
            return []

        return await self.add(
            trainer=trainer, owned_pokemon=owned_pokemon, without_throw=True
        )

    async def ready_to_battle(self, trainer: Trainer) -> TrainerParty:
        parties = await self.list_all(
            page_filter=FilterPage.build(trainer_id=trainer.id, is_active=True)
        )

        if not parties:
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.SHOWN,
                user_id=trainer.user.id,
                message="Trainer has no active party for battle",
                log_type=LogTypeEnum.PARTY,
            )
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Trainer has no active party for battle",
            )

        for party in parties:
            if party.owned_pokemon.hp > 0:
                return party
        await self.trainer_log.create(
            status=LogStatusEnum.ERROR,
            event=TrainerLogEventEnum.SHOWN,
            user_id=trainer.user.id,
            message="Trainer has no battle-ready Pokemon",
            log_type=LogTypeEnum.PARTY,
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Trainer has no battle-ready Pokemon",
        )
