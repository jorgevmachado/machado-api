from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.pagination import CustomLimitOffsetPage, is_paginate
from app.core.pagination.pagination import get_limit_offset_params
from app.core.repository.base import BaseRepository
from app.models import HealingLog, MyPokemon, PokemonCenterHealing
from app.shared.schemas import FilterPage


class PokemonCenterRepository(BaseRepository[PokemonCenterHealing]):
    model = PokemonCenterHealing
    default_order_by = "created_at"
    relations = (selectinload(PokemonCenterHealing.logs),)

    async def create_summary(self, entity: PokemonCenterHealing) -> PokemonCenterHealing:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def create_logs(self, entities: list[HealingLog]) -> list[HealingLog]:
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def find_latest_by_trainer_id(self, trainer_id: UUID) -> PokemonCenterHealing | None:
        query = (
            select(PokemonCenterHealing)
            .where(
                PokemonCenterHealing.trainer_id == trainer_id,
                PokemonCenterHealing.deleted_at.is_(None),
            )
            .order_by(PokemonCenterHealing.created_at.desc())
        )
        return await self.session.scalar(query)

    async def list_history(
        self,
        *,
        trainer_id: UUID,
        page_filter: FilterPage | None = None,
    ):
        query = (
            select(HealingLog)
            .options(selectinload(HealingLog.my_pokemon))
            .join(HealingLog.my_pokemon)
            .where(
                HealingLog.trainer_id == trainer_id,
                HealingLog.deleted_at.is_(None),
                MyPokemon.deleted_at.is_(None),
            )
            .order_by(HealingLog.created_at.desc())
        )

        if is_paginate(page_filter):
            params = get_limit_offset_params(page_filter)
            total_query = select(func.count()).select_from(query.order_by(None).subquery())
            total = int(await self.session.scalar(total_query) or 0)
            result = await self.session.scalars(query.limit(params.limit).offset(params.offset))
            return CustomLimitOffsetPage.create(
                items=result.all(),
                total=total,
                params=params,
            )

        result = await self.session.scalars(query)
        return result.all()
