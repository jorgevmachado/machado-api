from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository.base import BaseRepository
from app.models import (
    MyPokemon,
    WildPokemonBattleLog,
    WildPokemonBattleSession,
    WildPokemonBattleTurn,
)
from app.models.enums import BattleSessionStatusEnum


class WildPokemonBattleSessionRepository(BaseRepository[WildPokemonBattleSession]):
    model = WildPokemonBattleSession
    relations = (
        selectinload(WildPokemonBattleSession.turns),
        selectinload(WildPokemonBattleSession.logs),
        selectinload(WildPokemonBattleSession.trainer_active_my_pokemon),
        selectinload(WildPokemonBattleSession.wild_pokemon),
        selectinload(WildPokemonBattleSession.exploration_event),
    )

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def find_active_by_trainer_id(
        self,
        trainer_id: UUID,
    ) -> WildPokemonBattleSession | None:
        query = select(WildPokemonBattleSession).where(
            WildPokemonBattleSession.trainer_id == trainer_id,
            WildPokemonBattleSession.status == BattleSessionStatusEnum.ACTIVE,
            WildPokemonBattleSession.deleted_at.is_(None),
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def find_by_id_and_trainer_id(
        self,
        session_id: UUID,
        trainer_id: UUID,
    ) -> WildPokemonBattleSession | None:
        query = select(WildPokemonBattleSession).where(
            WildPokemonBattleSession.id == session_id,
            WildPokemonBattleSession.trainer_id == trainer_id,
            WildPokemonBattleSession.deleted_at.is_(None),
        )
        for option in self.relations:
            query = query.options(option)
        return await self.session.scalar(query)

    async def create_session(
        self,
        entity: WildPokemonBattleSession,
    ) -> WildPokemonBattleSession:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_turn(
        self,
        entity: WildPokemonBattleTurn,
    ) -> WildPokemonBattleTurn:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_log(
        self,
        entity: WildPokemonBattleLog,
    ) -> WildPokemonBattleLog:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list_logs(
        self,
        battle_session_id: UUID,
    ) -> list[WildPokemonBattleLog]:
        query = (
            select(WildPokemonBattleLog)
            .where(WildPokemonBattleLog.battle_session_id == battle_session_id)
            .order_by(WildPokemonBattleLog.created_at)
        )
        result = await self.session.scalars(query)
        return result.all()

    async def list_turns(
        self,
        battle_session_id: UUID,
    ) -> list[WildPokemonBattleTurn]:
        query = (
            select(WildPokemonBattleTurn)
            .where(WildPokemonBattleTurn.battle_session_id == battle_session_id)
            .order_by(WildPokemonBattleTurn.created_at)
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
