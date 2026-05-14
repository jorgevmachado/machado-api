from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.domain.trainer.schema import (
    OnboardingTrainerSchema,
    TrainerOnboardingResponseSchema,
)
from app.domain.trainer.service import TrainerService
from app.models import User

router = APIRouter(prefix="/trainer", tags=["trainer"])

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_service(session: Session) -> TrainerService:
    return TrainerService.from_session(session)


@router.post(
    "/onboarding",
    response_model=TrainerOnboardingResponseSchema,
    status_code=HTTPStatus.CREATED,
)
async def onboard_trainer(
    payload: OnboardingTrainerSchema,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TrainerService, Depends(get_trainer_service)],
):
    return await service.onboard(current_user, payload)
