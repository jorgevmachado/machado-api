from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security import get_current_user
from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.schema import PokemonSchema
from app.domain.pokemon.service import PokemonService
from app.models import User
from app.shared.schemas import FilterPage

from app.domain.pokemon.ability.route import router as pokemon_ability_router
from app.domain.pokemon.move.route import router as pokemon_move_router
from app.domain.pokemon.type.route import router as pokemon_type_router
from app.domain.pokemon.habitat.route import router as pokemon_habitat_router
from app.domain.pokemon.growth_rate.route import router as pokemon_growth_rate_router
from app.domain.pokemon.encounter.route import router as pokemon_encounter_router

router = APIRouter(prefix="/pokemon", tags=["pokemon"])
router.include_router(
    pokemon_ability_router, prefix="/ability", tags=["PokemonAbility"]
)
router.include_router(pokemon_move_router, prefix="/move", tags=["PokemonMove"])
router.include_router(pokemon_type_router, prefix="/type", tags=["PokemonType"])
router.include_router(
    pokemon_habitat_router, prefix="/habitat", tags=["PokemonHabitat"]
)
router.include_router(
    pokemon_growth_rate_router, prefix="/growth-rate", tags=["PokemonGrowthRate"]
)
router.include_router(
    pokemon_encounter_router, prefix="/encounter", tags=["PokemonEncounter"]
)

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokemon_service(session: Session) -> PokemonService:
    return PokemonService(PokemonRepository(session))


def get_pokemon_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    name: str | None = None,
    order: int | None = None,
    status: str | None = None,
    type: str | None = None,  # noqa: A002
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        name=name,
        order=order,
        status=status,
        type=type,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[PokemonSchema] | list[PokemonSchema],
    status_code=HTTPStatus.OK,
)
async def list_pokemons(
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonService, Depends(get_pokemon_service)],
    page_filter: Annotated[FilterPage, Depends(get_pokemon_filter)],
):
    return await service.list_all_cached(page_filter=page_filter)


@router.get("/{identifier}", response_model=PokemonSchema, status_code=HTTPStatus.OK)
async def get_pokemon(
    identifier: str,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokemonService, Depends(get_pokemon_service)],
):
    return await service.find_detail(identifier)
