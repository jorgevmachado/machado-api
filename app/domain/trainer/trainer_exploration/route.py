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
    TrainerHomeSchema,
    TrainerPartyMemberSchema,
    UpdateTrainerPartySchema,
)
from app.domain.trainer.trainer_exploration.service import TrainerExplorationService
from app.models import User

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_exploration_service(session: Session) -> TrainerExplorationService:
    return TrainerExplorationService.from_session(session)


@router.get("/home", response_model=TrainerHomeSchema, status_code=HTTPStatus.OK)
async def get_trainer_home(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        TrainerExplorationService,
        Depends(get_trainer_exploration_service),
    ],
):
    return await service.get_home(current_user)


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


@router.put("/party", response_model=list[TrainerPartyMemberSchema], status_code=HTTPStatus.OK)
async def update_trainer_party(
    payload: UpdateTrainerPartySchema,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        TrainerExplorationService,
        Depends(get_trainer_exploration_service),
    ],
):
    return await service.update_party(current_user, payload)


@router.post("/walk", response_model=ExplorationEventSchema, status_code=HTTPStatus.OK)
async def walk_trainer_encounter(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        TrainerExplorationService,
        Depends(get_trainer_exploration_service),
    ],
):
    return await service.walk(current_user)
