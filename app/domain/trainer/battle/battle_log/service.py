from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.trainer.battle.battle_log.repository import BattleLogRepository
from app.domain.trainer.battle.battle_log.schema import (
    BattleLogSchema,
)
from app.models import BattleLog
from app.models.enums import BattleActorEnum, BattleLogTypeEnum

logger = logging.getLogger(__name__)


class BattleLogService(BaseService[BattleLogRepository, BattleLog]):
    def __init__(
        self,
        repository: BattleLogRepository,
    ) -> None:
        super().__init__(
            alias="BattleLog",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="BattleLogService",
                operation="trainer.battle.battle_log",
            ),
            schema_class=BattleLogSchema,
            cache_prefix="battle_log",
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(BattleLogRepository(session))

    async def start(
        self,
        payload: dict,
        battle_session_id: UUID,
    ) -> BattleLog:
        return await self.repository.save(
            entity=BattleLog(
                message=f"Wild {payload['pokemon_name']} battle started",
                log_type=BattleLogTypeEnum.SESSION_STARTED,
                actor=BattleActorEnum.TRAINER,
                payload=payload,
                battle_session_id=battle_session_id,
            )
        )
