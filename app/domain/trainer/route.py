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
from app.domain.trainer.pokedex.route import router as pokedex_router
from app.domain.trainer.my_pokemon.route import router as my_pokemon_router
from app.domain.trainer.trainer_exploration.route import router as trainer_exploration_router

router = APIRouter(prefix="/trainer", tags=["trainer"])
router.include_router(pokedex_router, prefix="/pokedex", tags=["Pokedex"])
router.include_router(my_pokemon_router, prefix="/my-pokemon", tags=["My Pokemon"])
router.include_router(trainer_exploration_router, prefix="/exploration", tags=["Trainer Exploration"])

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
