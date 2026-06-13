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

from app.domain.trainer.encounter.repository import TrainerEncounterRepository
from app.domain.trainer.encounter.schema import (
    TrainerEncounterSchema,
    ActiveTrainerEncounterPayloadSchema,
)
from app.domain.trainer.encounter.service import TrainerEncounterService

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_encounter_service(session: Session) -> TrainerEncounterService:
    return TrainerEncounterService(TrainerEncounterRepository(session))


Service = Annotated[TrainerEncounterService, Depends(get_trainer_encounter_service)]
CurrentTrainer = Annotated[Trainer, Depends(get_current_trainer)]


def get_encounter_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    pokemon_encounter_id: str | None = None,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        pokemon_encounter_id=pokemon_encounter_id,
        clean_cache=clean_cache,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[TrainerEncounterSchema]
    | list[TrainerEncounterSchema],
    status_code=HTTPStatus.OK,
)
async def list_all(
    service: Service,
    current_trainer: CurrentTrainer,
    page_filter: Annotated[FilterPage, Depends(get_encounter_filter)] = None,
):
    return await service.list_all_cached(
        page_filter=FilterPage.build(page_filter, trainer_id=current_trainer.id),
        user_request=current_trainer.user.username,
    )


@router.get(
    "/{param}", response_model=TrainerEncounterSchema, status_code=HTTPStatus.OK
)
async def find_one(param: str, service: Service, current_trainer: CurrentTrainer):
    return await service.find_one_cached(
        param=param,
        user_request=current_trainer.user.username,
        trainer_id=current_trainer.id,
    )


@router.put(
    "/active",
    response_model=TrainerEncounterSchema,
    status_code=HTTPStatus.OK,
)
async def select_active(
    payload: ActiveTrainerEncounterPayloadSchema,
    service: Service,
    current_trainer: CurrentTrainer,
):
    return await service.select_active(
        trainer=current_trainer, encounter_id=payload.encounter_id
    )
