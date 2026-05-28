from __future__ import annotations

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security import get_current_user

from app.models.user import User

from app.shared.schemas import FilterPage

from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.schema import PokemonSchema
from app.domain.pokemon.service import PokemonService

from app.domain.pokemon.ability.route import router as ability_router
from app.domain.pokemon.move.route import router as move_router
from app.domain.pokemon.type.route import router as type_router
from app.domain.pokemon.habitat.route import router as habitat_router
from app.domain.pokemon.growth_rate.route import router as growth_rate_router
from app.domain.pokemon.encounter.route import router as encounter_router

router = APIRouter(prefix="/pokemon", tags=["Pokemon"])
router.include_router(ability_router, prefix="/ability", tags=["PokemonAbility"])
router.include_router(move_router, prefix="/move", tags=["PokemonMove"])
router.include_router(type_router, prefix="/type", tags=["PokemonType"])
router.include_router(habitat_router, prefix="/habitat", tags=["PokemonHabitat"])
router.include_router(
    growth_rate_router, prefix="/growth-rate", tags=["PokemonGrowthRate"]
)
router.include_router(encounter_router, prefix="/encounter", tags=["PokemonEncounter"])

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokemon_service(session: Session) -> PokemonService:
    return PokemonService(PokemonRepository(session))


Service = Annotated[PokemonService, Depends(get_pokemon_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_pokemon_filter(
    type: str | None = None,  # noqa: A002
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    name: str | None = None,
    order: int | None = None,
    status: str | None = None,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        type=type,
        page=page,
        offset=offset,
        limit=limit,
        name=name,
        order=order,
        status=status,
        clean_cache=clean_cache,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[PokemonSchema] | list[PokemonSchema],
    status_code=HTTPStatus.OK,
)
async def list_all(
    service: Service,
    current_user: CurrentUser,
    page_filter: Annotated[FilterPage, Depends(get_pokemon_filter)] = None,
):
    return await service.list_all_cached(
        page_filter=page_filter,
        user_request=current_user.username,
    )


@router.get("/{param}", response_model=PokemonSchema, status_code=HTTPStatus.OK)
async def find_one(
    param: str,
    service: Service,
    current_user: CurrentUser,
    clean_cache: bool = False,
):
    return await service.find_one_cached(
        param=param,
        user_request=current_user.username,
        clean_cache=clean_cache,
    )
