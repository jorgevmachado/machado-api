from __future__ import annotations

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security import get_current_trainer
from app.models import Trainer

from app.shared.schemas import FilterPage

from app.domain.trainer.battle.repository import BattleRepository
from app.domain.trainer.battle.schema import BattleSchema
from app.domain.trainer.battle.service import BattleService

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_battle_service(session: Session) -> BattleService:
    return BattleService(BattleRepository(session))


Service = Annotated[BattleService, Depends(get_battle_service)]
CurrentTrainer = Annotated[Trainer, Depends(get_current_trainer)]


def get_battle_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    name: str | None = None,
    order: int | None = None,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        name=name,
        order=order,
        clean_cache=clean_cache,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[BattleSchema] | list[BattleSchema],
    status_code=HTTPStatus.OK,
)
async def list_all(
    service: Service,
    current_trainer: CurrentTrainer,
    page_filter: Annotated[FilterPage, Depends(get_battle_filter)] = None,
):
    return await service.list_all_cached(
        page_filter=FilterPage.build(page_filter, trainer_id=current_trainer.id),
        user_request=current_trainer.user.username,
    )


@router.get("/{param}", response_model=BattleSchema, status_code=HTTPStatus.OK)
async def find_one(param: str, service: Service, current_trainer: CurrentTrainer):
    return await service.find_one_cached(
        param=param,
        trainer_id=current_trainer.id,
        user_request=current_trainer.user.username,
    )
