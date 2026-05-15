from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security import get_current_user
from app.domain.trainer.my_pokemon.repository import MyPokemonRepository
from app.domain.trainer.my_pokemon.schema import (
    CreateMyPokemonSchema,
    MyPokemonSchema,
)
from app.domain.trainer.my_pokemon.service import MyPokemonService
from app.models import User
from app.shared.schemas import FilterPage

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_my_pokemon_service(session: Session) -> MyPokemonService:
    return MyPokemonService(MyPokemonRepository(session))


def get_my_pokemon_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    name: str | None = None,
    pokemon_name: str | None = None,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        name=name,
        pokemon_name=pokemon_name,
        clean_cache=clean_cache,
    )


@router.post("", response_model=MyPokemonSchema, status_code=HTTPStatus.CREATED)
async def create_my_pokemon(
    payload: CreateMyPokemonSchema,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MyPokemonService, Depends(get_my_pokemon_service)],
):
    return await service.create(current_user, payload)


@router.get(
    "",
    response_model=CustomLimitOffsetPage[MyPokemonSchema] | list[MyPokemonSchema],
    status_code=HTTPStatus.OK,
)
async def list_my_pokemon(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MyPokemonService, Depends(get_my_pokemon_service)],
    page_filter: Annotated[FilterPage, Depends(get_my_pokemon_filter)],
):
    return await service.list_all_cached(current_user, page_filter)


@router.get("/{name}", response_model=MyPokemonSchema, status_code=HTTPStatus.OK)
async def get_my_pokemon(
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MyPokemonService, Depends(get_my_pokemon_service)],
):
    return await service.find_detail(current_user, name)
