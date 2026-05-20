from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security.security import get_current_trainer
from app.domain.trainer.wild_pokemon_battle_session.schema import (
    BattleLogSchema,
    SwitchBattlePokemonSchema,
    UseBattleMoveSchema,
    WildPokemonBattleSessionSchema,
)
from app.domain.trainer.wild_pokemon_battle_session.service import (
    WildPokemonBattleSessionService,
)
from app.models import Trainer

router = APIRouter(prefix="/battle", tags=["Wild Pokemon Battle Session"])

Session = Annotated[AsyncSession, Depends(get_session)]


def get_wild_pokemon_battle_session_service(
    session: Session,
) -> WildPokemonBattleSessionService:
    return WildPokemonBattleSessionService.from_session(session)


@router.get(
    "/active",
    response_model=WildPokemonBattleSessionSchema,
    status_code=HTTPStatus.OK,
)
async def get_active_battle(
    current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
    service: Annotated[
        WildPokemonBattleSessionService,
        Depends(get_wild_pokemon_battle_session_service),
    ],
):
    return await service.get_active_battle(current_trainer)


@router.post(
    "/move",
    response_model=WildPokemonBattleSessionSchema,
    status_code=HTTPStatus.OK,
)
async def use_battle_move(
    payload: UseBattleMoveSchema,
    current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
    service: Annotated[
        WildPokemonBattleSessionService,
        Depends(get_wild_pokemon_battle_session_service),
    ],
):
    return await service.use_move(current_trainer, payload)


@router.post(
    "/switch",
    response_model=WildPokemonBattleSessionSchema,
    status_code=HTTPStatus.OK,
)
async def switch_battle_pokemon(
    payload: SwitchBattlePokemonSchema,
    current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
    service: Annotated[
        WildPokemonBattleSessionService,
        Depends(get_wild_pokemon_battle_session_service),
    ],
):
    return await service.switch_pokemon(current_trainer, payload)


@router.post(
    "/flee",
    response_model=WildPokemonBattleSessionSchema,
    status_code=HTTPStatus.OK,
)
async def flee_battle(
    current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
    service: Annotated[
        WildPokemonBattleSessionService,
        Depends(get_wild_pokemon_battle_session_service),
    ],
):
    return await service.flee(current_trainer)


@router.get(
    "/logs",
    response_model=list[BattleLogSchema],
    status_code=HTTPStatus.OK,
)
async def list_battle_logs(
    current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
    service: Annotated[
        WildPokemonBattleSessionService,
        Depends(get_wild_pokemon_battle_session_service),
    ],
):
    return await service.list_logs(current_trainer)
