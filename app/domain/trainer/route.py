from __future__ import annotations

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user

from app.domain.trainer.schema import OnboardPayloadSchema, TrainerSchema

from app.models import User

from app.domain.trainer.service import TrainerService

from app.domain.trainer.encounter.route import router as trainer_encounter_router
from app.domain.trainer.owned_pokemon.route import router as owned_pokemon_router
from app.domain.trainer.pokedex.route import router as pokedex_router

router = APIRouter(prefix="/trainer", tags=["trainer"])
router.include_router(
    trainer_encounter_router, prefix="/encounter", tags=["TrainerEncounter"]
)
router.include_router(owned_pokemon_router, prefix="/pokemon", tags=["OwnedPokemon"])
router.include_router(pokedex_router, prefix="/pokedex", tags=["Pokedex"])

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_service(session: Session) -> TrainerService:
    return TrainerService.from_session(session)


Service = Annotated[TrainerService, Depends(get_trainer_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/onboarding", response_model=TrainerSchema, status_code=HTTPStatus.CREATED
)
async def onboarding(
    payload: OnboardPayloadSchema, service: Service, current_user: CurrentUser
):
    return await service.onboard(current_user=current_user, payload=payload)
