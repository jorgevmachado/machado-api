from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.domain.trainer.battle.route import router as battle_router
from app.domain.trainer.encounter.route import router as trainer_encounter_router
from app.domain.trainer.encounter.schema import TrainerHomeSchema
from app.domain.trainer.my_pokemon.route import router as my_pokemon_router
from app.domain.trainer.pokedex.route import router as pokedex_router
from app.domain.trainer.schema import (
    OnboardingTrainerSchema,
    TrainerOnboardingResponseSchema, TrainerSchema,
)
from app.domain.trainer.service import TrainerService
from app.domain.trainer.trainer_party.route import router as trainer_party_router
from app.models import User, Trainer

router = APIRouter(prefix="/trainer", tags=["trainer"])
router.include_router(pokedex_router, prefix="/pokedex", tags=["Pokedex"])
router.include_router(my_pokemon_router, prefix="/my-pokemon", tags=["My Pokemon"])
router.include_router(trainer_party_router, tags=["Trainer Party"])
router.include_router(trainer_encounter_router, prefix="/encounter", tags=["Trainer Encounter"])
router.include_router(battle_router, tags=["Battle Session"])

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_service(session: Session) -> TrainerService:
    return TrainerService.from_session(session)


@router.get("/me", response_model=TrainerSchema, status_code=HTTPStatus.OK)
async def get_current_trainer(
        current_user: Annotated[User, Depends(get_current_user)],
        service: Annotated[TrainerService, Depends(get_trainer_service)],
):
    return await service.find_by(user_id=str(current_user.id))


@router.get("/home", response_model=TrainerHomeSchema, status_code=HTTPStatus.OK)
async def get_trainer_home(
        current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
        service: Annotated[TrainerService, Depends(get_trainer_service)],
):
    return await service.get_home(trainer=current_trainer)


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
