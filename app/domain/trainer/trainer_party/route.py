from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.domain.trainer.trainer_party.schema import (
    TrainerPartyMemberSchema,
    UpdateTrainerPartySchema,
)
from app.domain.trainer.trainer_party.service import TrainerPartyService
from app.models import User

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_trainer_party_service(session: Session) -> TrainerPartyService:
    return TrainerPartyService.from_session(session)


@router.get("/party", response_model=list[TrainerPartyMemberSchema], status_code=HTTPStatus.OK)
async def get_trainer_party(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TrainerPartyService, Depends(get_trainer_party_service)],
):
    return await service.get_party(current_user)


@router.put("/party", response_model=list[TrainerPartyMemberSchema], status_code=HTTPStatus.OK)
async def update_trainer_party(
    payload: UpdateTrainerPartySchema,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TrainerPartyService, Depends(get_trainer_party_service)],
):
    return await service.update_party(current_user, payload)
