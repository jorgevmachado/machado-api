from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.domain.pokemon.ability.repository import PokemonAbilityRepository
from app.core.pagination.schemas import CustomLimitOffsetPage
from app.domain.pokemon.ability.service import PokemonAbilityService
from app.domain.pokemon.ability.schema import PokemonAbilitySchema
from app.models import User
from app.shared.schemas import FilterPage

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokemon_ability_service(session: Session) -> PokemonAbilityService:
    return PokemonAbilityService(PokemonAbilityRepository(session))


def get_pokemon_ability_filter(
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
    response_model=CustomLimitOffsetPage[PokemonAbilitySchema]
    | list[PokemonAbilitySchema],
    status_code=HTTPStatus.OK,
)
async def list_pokemon_abilities(
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonAbilityService, Depends(get_pokemon_ability_service)],
    page_filter: Annotated[FilterPage, Depends(get_pokemon_ability_filter)] = None,
):
    return await service.list_all_cached(page_filter=page_filter)


@router.get(
    "/{identifier}", response_model=PokemonAbilitySchema, status_code=HTTPStatus.OK
)
async def get_pokemon_ability(
    identifier: str,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonAbilityService, Depends(get_pokemon_ability_service)],
):
    return await service.find_one_cached(param=identifier)
