from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.domain.pokemon.move.repository import PokemonMoveRepository
from app.core.pagination.schemas import CustomLimitOffsetPage
from app.domain.pokemon.move.service import PokemonMoveService
from app.domain.pokemon.move.schema import PokemonMoveSchema
from app.models import User
from app.shared.schemas import FilterPage

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokemon_move_service(session: Session) -> PokemonMoveService:
    return PokemonMoveService(PokemonMoveRepository(session))


def get_pokemon_move_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    name: str | None = None,
    order: int | None = None,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        name=name,
        order=order,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[PokemonMoveSchema] | list[PokemonMoveSchema],
    status_code=HTTPStatus.OK,
)
async def list_pokemon_move(
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonMoveService, Depends(get_pokemon_move_service)],
    page_filter: Annotated[FilterPage, Depends(get_pokemon_move_filter)] = None,
):
    return await service.list_all_cached(page_filter=page_filter)


@router.get(
    "/{identifier}", response_model=PokemonMoveSchema, status_code=HTTPStatus.OK
)
async def get_pokemon_move(
    identifier: str,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonMoveService, Depends(get_pokemon_move_service)],
):
    return await service.find_one_cached(param=identifier)
