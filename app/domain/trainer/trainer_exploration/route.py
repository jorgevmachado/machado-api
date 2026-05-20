from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.domain.trainer.trainer_exploration.schema import (
    ExplorationEventSchema,
    SelectTrainerEncounterSchema,
    TrainerEncounterSchema,
)
from app.domain.trainer.trainer_exploration.service import TrainerExplorationService
from app.models import User

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_exploration_service(session: Session) -> TrainerExplorationService:
    return TrainerExplorationService.from_session(session)


@router.get(
    "/encounters",
    response_model=list[TrainerEncounterSchema],
    status_code=HTTPStatus.OK,
)
async def list_trainer_encounters(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        TrainerExplorationService,
        Depends(get_trainer_exploration_service),
    ],
):
    return await service.list_encounters(current_user)


@router.put(
    "/encounters/active",
    response_model=TrainerEncounterSchema,
    status_code=HTTPStatus.OK,
)
async def select_active_trainer_encounter(
    payload: SelectTrainerEncounterSchema,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        TrainerExplorationService,
        Depends(get_trainer_exploration_service),
    ],
):
    return await service.select_active_encounter(current_user, payload)


@router.post("/walk", response_model=ExplorationEventSchema, status_code=HTTPStatus.OK)
async def walk_trainer_encounter(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        TrainerExplorationService,
        Depends(get_trainer_exploration_service),
    ],
):
    return await service.walk(current_user)
