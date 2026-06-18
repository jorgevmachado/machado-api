from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.trainer.battle.battle_log.service import BattleLogService
from app.domain.trainer.battle.business import (
    build_trainer_party_snapshot,
    build_wild_pokemon_snapshot,
    build_payload,
)
from app.domain.trainer.battle.repository import BattleRepository
from app.domain.trainer.battle.schema import (
    BattleSchema,
    BattleProcessedSchema,
)
from app.domain.trainer.pokedex.service import PokedexService
from app.domain.trainer.trainer_log.service import TrainerLogService
from app.models import (
    BattleSession,
    ExplorationEvent,
    Trainer,
    TrainerParty,
    PokedexEntry,
    utcnow,
)
from app.models.enums import (
    BattleSessionStatusEnum,
    LogStatusEnum,
    TrainerLogEventEnum,
    LogTypeEnum,
    BattleActorEnum,
    BattleLogTypeEnum,
)

logger = logging.getLogger(__name__)


class BattleService(BaseService[BattleRepository, BattleSession]):
    def __init__(
        self,
        repository: BattleRepository,
        trainer_log: TrainerLogService | None = None,
        pokedex_service: PokedexService | None = None,
        battle_log_service: BattleLogService | None = None,
    ) -> None:
        super().__init__(
            alias="Battle",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="BattleService",
                operation="trainer.battle",
            ),
            schema_class=BattleSchema,
            cache_prefix="battle",
        )
        session = repository.session
        self.trainer_log = trainer_log or TrainerLogService.from_session(session)
        self.pokedex_service = pokedex_service or PokedexService.from_session(session)
        self.battle_log_service = battle_log_service or BattleLogService.from_session(
            session
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(BattleRepository(session))

    async def create_or_resume(
        self,
        party: TrainerParty,
        trainer: Trainer,
        exploration_event: ExplorationEvent,
    ) -> BattleSession:
        active = await self.find_by(
            trainer_id=trainer.id,
            status=BattleSessionStatusEnum.ACTIVE,
            without_throw=True,
        )
        if active is not None:
            return active

        trainer_party_snapshot = build_trainer_party_snapshot(party)

        wild_pokemon_name = exploration_event.payload["wild_pokemon_name"]
        wild_pokemon = await self.pokedex_service.find_one_cached(
            param=wild_pokemon_name, trainer_id=trainer.id
        )

        wild_pokemon_snapshot = build_wild_pokemon_snapshot(wild_pokemon)

        payload = build_payload(
            message="Battle session started",
            wild_pokemon=wild_pokemon,
            trainer_active_pokemon=party.owned_pokemon,
        )

        entity = await self.repository.save(
            entity=BattleSession(
                status=BattleSessionStatusEnum.ACTIVE,
                trainer_id=trainer.id,
                wild_pokemon_id=wild_pokemon.id,
                exploration_event_id=exploration_event.id,
                wild_pokemon_snapshot=wild_pokemon_snapshot,
                trainer_party_snapshot=trainer_party_snapshot,
                trainer_active_owned_pokemon_id=party.owned_pokemon.id,
            )
        )

        setattr(entity, "_trainer_context", trainer)
        await self.battle_log_service.start(
            battle_session_id=entity.id,
            payload={
                **(payload or {}),
                "exploration_event_id": str(exploration_event.id),
            },
        )

        return entity

    async def get(
        self,
        trainer: Trainer,
        status: BattleSessionStatusEnum = BattleSessionStatusEnum.ACTIVE,
        battle_id: str | None = None,
    ) -> BattleSession:
        if battle_id:
            battle_session = await self.find_one(param=battle_id, trainer_id=trainer.id)
        else:
            battle_session = await self.find_by(
                status=status,
                trainer_id=trainer.id,
                without_throw=True,
            )

        if not battle_session:
            message = "Trainer has no active battle"
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.BATTLE,
                user_id=trainer.user.id,
                message=message,
                payload={
                    "battle_session_id": battle_id,
                    "battle_session_status": status,
                },
                log_type=LogTypeEnum.TRAINER,
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=message,
            )
        if battle_session.status != BattleSessionStatusEnum.ACTIVE:
            message = f"Battle session finish with {battle_session.status.value} status"
            await self.trainer_log.create(
                status=LogStatusEnum.ERROR,
                event=TrainerLogEventEnum.BATTLE,
                user_id=trainer.user.id,
                message=message,
                payload={
                    "battle_session_id": battle_id,
                    "battle_session_status": battle_session.status,
                },
                log_type=LogTypeEnum.TRAINER,
            )
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=message,
            )

        return battle_session

    async def persist(
        self,
        wild_pokemon: PokedexEntry,
        trainer_party: TrainerParty,
        battle_session: BattleSession,
        battle_result: BattleProcessedSchema,
        persist_type: BattleLogTypeEnum = BattleLogTypeEnum.MOVE_USED,
    ) -> BattleSession:

        battle_session.status = battle_result.status

        payload = build_payload(
            wild_pokemon=wild_pokemon,
            battle_result=battle_result,
            trainer_active_pokemon=trainer_party.owned_pokemon,
        )

        battle_session.wild_pokemon_snapshot = build_wild_pokemon_snapshot(wild_pokemon)
        battle_session.trainer_party_snapshot = build_trainer_party_snapshot(
            trainer_party
        )

        battle_session.trainer_active_owned_pokemon_id = trainer_party.owned_pokemon.id

        if not battle_result.error:
            battle_session.turn_number += 1
        battle_session.updated_at = utcnow()
        updated_battle_session = await self.repository.update(entity=battle_session)

        await self.battle_log_service.create(
            actor=BattleActorEnum.TRAINER,
            payload={
                **(payload or {}),
                "exploration_event_id": str(battle_session.exploration_event_id),
            },
            message=payload["message"],
            log_type=persist_type,
            battle_session_id=updated_battle_session.id,
        )

        return updated_battle_session
