from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security.security import get_current_trainer
from app.domain.trainer.pokemon_center.schema import (
    HealingLogHistorySchema,
    PokemonCenterHealingResultSchema,
)
from app.domain.trainer.pokemon_center.service import PokemonCenterService
from app.models import Trainer
from app.shared.schemas import FilterPage

router = APIRouter(prefix="/pokemon-center")

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokemon_center_service(session: Session) -> PokemonCenterService:
    return PokemonCenterService.from_session(session)


def get_healing_history_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        clean_cache=clean_cache,
    )


@router.post("/heal", response_model=PokemonCenterHealingResultSchema, status_code=HTTPStatus.OK)
async def heal_pokemon_center_party(
    current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
    service: Annotated[PokemonCenterService, Depends(get_pokemon_center_service)],
):
    return await service.heal_party(current_trainer)


@router.get(
    "/healing-history",
    response_model=CustomLimitOffsetPage[HealingLogHistorySchema] | list[HealingLogHistorySchema],
    status_code=HTTPStatus.OK,
)
async def list_healing_history(
    current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
    service: Annotated[PokemonCenterService, Depends(get_pokemon_center_service)],
    page_filter: Annotated[FilterPage, Depends(get_healing_history_filter)],
):
    return await service.list_history(current_trainer, page_filter)
