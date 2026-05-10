from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.domain.pokemon.habitat.repository import PokemonHabitatRepository
from app.core.pagination.schemas import CustomLimitOffsetPage
from app.domain.pokemon.habitat.service import PokemonHabitatService
from app.domain.pokemon.habitat.schema import PokemonHabitatSchema
from app.models import User
from app.shared.schemas import FilterPage

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokemon_habitat_service(session: Session) -> PokemonHabitatService:
    return PokemonHabitatService(PokemonHabitatRepository(session))


def get_pokemon_habitat_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    name: str | None = None,
    order: int | None = None,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        name=name,
        order=order,
        clean_cache=clean_cache,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[PokemonHabitatSchema]
    | list[PokemonHabitatSchema],
    status_code=HTTPStatus.OK,
)
async def list_pokemon_habitat(
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonHabitatService, Depends(get_pokemon_habitat_service)],
    page_filter: Annotated[FilterPage, Depends(get_pokemon_habitat_filter)] = None,
):
    return await service.list_all_cached(page_filter=page_filter)


@router.get(
    "/{identifier}", response_model=PokemonHabitatSchema, status_code=HTTPStatus.OK
)
async def get_pokemon_habitat(
    identifier: str,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonHabitatService, Depends(get_pokemon_habitat_service)],
):
    return await service.find_one_cached(param=identifier)
