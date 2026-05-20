from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security import get_current_user
from app.core.security.security import get_current_trainer
from app.domain.trainer.encounter.schema import (
    ExplorationEventSchema,
    SelectTrainerEncounterSchema,
    TrainerEncounterSchema,
)
from app.domain.trainer.encounter.service import TrainerEncounterService
from app.models import User, Trainer
from app.shared.schemas import FilterPage

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_encounter_service(session: Session) -> TrainerEncounterService:
    return TrainerEncounterService.from_session(session)


def get_trainer_encounter_filter(
        page: int | None = None,
        offset: int | None = None,
        limit: int | None = 12,
        is_active: bool | None = None,
        clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        is_active=is_active,
        clean_cache=clean_cache,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[TrainerEncounterSchema] | list[TrainerEncounterSchema],
    status_code=HTTPStatus.OK,
)
async def list_trainer_encounters(
        current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
        service: Annotated[
            TrainerEncounterService,
            Depends(get_trainer_encounter_service),
        ],
        page_filter: Annotated[FilterPage, Depends(get_trainer_encounter_filter)],
):
    filters = FilterPage.build(page_filter, trainer_id=str(current_trainer.id))
    return await service.list_all_cached(page_filter=filters)


@router.put(
    "/active",
    response_model=TrainerEncounterSchema,
    status_code=HTTPStatus.OK,
)
async def select_active_trainer_encounter(
        payload: SelectTrainerEncounterSchema,
        current_user: Annotated[User, Depends(get_current_user)],
        service: Annotated[
            TrainerEncounterService,
            Depends(get_trainer_encounter_service),
        ],
):
    return await service.select_active_encounter(current_user, payload)


@router.post("/walk", response_model=ExplorationEventSchema, status_code=HTTPStatus.OK)
async def walk_trainer_encounter(
        current_user: Annotated[User, Depends(get_current_user)],
        service: Annotated[
            TrainerEncounterService,
            Depends(get_trainer_encounter_service),
        ],
):
    return await service.walk(current_user)
