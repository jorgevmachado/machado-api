from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import (
    BattleLog,
    BattleSession,
    BattleTurn,
    MyPokemon,
)
from app.models.enums import BattleSessionStatusEnum


class BattleSessionRepository(BaseRepository[BattleSession]):
    model = BattleSession
    relations = (
        selectinload(BattleSession.turns),
        selectinload(BattleSession.logs),
        selectinload(BattleSession.trainer_active_my_pokemon),
        selectinload(BattleSession.wild_pokemon),
        selectinload(BattleSession.exploration_event),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def find_active_by_trainer_id(
        self,
        trainer_id: UUID,
    ) -> BattleSession | None:
        query = select(BattleSession).where(
            BattleSession.trainer_id == trainer_id,
            BattleSession.status == BattleSessionStatusEnum.ACTIVE,
            BattleSession.deleted_at.is_(None),
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def find_by_id_and_trainer_id(
        self,
        session_id: UUID,
        trainer_id: UUID,
    ) -> BattleSession | None:
        query = select(BattleSession).where(
            BattleSession.id == session_id,
            BattleSession.trainer_id == trainer_id,
            BattleSession.deleted_at.is_(None),
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def find_latest_by_trainer_id(
        self,
        trainer_id: UUID,
    ) -> BattleSession | None:
        query = (
            select(BattleSession)
            .where(
                BattleSession.trainer_id == trainer_id,
                BattleSession.deleted_at.is_(None),
            )
            .order_by(BattleSession.created_at.desc())
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def create_session(
        self,
        entity: BattleSession,
    ) -> BattleSession:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_turn(
        self,
        entity: BattleTurn,
    ) -> BattleTurn:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_log(
        self,
        entity: BattleLog,
    ) -> BattleLog:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list_logs(
        self,
        battle_session_id: UUID,
    ) -> list[BattleLog]:
        query = (
            select(BattleLog)
            .where(BattleLog.battle_session_id == battle_session_id)
            .order_by(BattleLog.created_at)
        )
        result = await self.session.scalars(query)
        return result.all()

    async def list_turns(
        self,
        battle_session_id: UUID,
    ) -> list[BattleTurn]:
        query = (
            select(BattleTurn)
            .where(BattleTurn.battle_session_id == battle_session_id)
            .order_by(BattleTurn.created_at)
        )
        result = await self.session.scalars(query)
        return result.all()

    async def list_available_party_members(
        self,
        trainer_id: UUID,
    ) -> list[MyPokemon]:
        query = select(MyPokemon).where(
            MyPokemon.trainer_id == trainer_id,
            MyPokemon.deleted_at.is_(None),
        )
        result = await self.session.scalars(query)
        return result.all()
