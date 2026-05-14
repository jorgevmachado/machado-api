from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security import get_current_user
from app.domain.pokedex.repository import PokedexRepository
from app.domain.pokedex.schema import PokedexSchema
from app.domain.pokedex.service import PokedexService
from app.models import User
from app.shared.schemas import FilterPage

router = APIRouter(prefix="/pokedex", tags=["pokedex"])

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokedex_service(session: Session) -> PokedexService:
    return PokedexService(PokedexRepository(session))


def get_pokedex_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    nickname: str | None = None,
    pokemon_name: str | None = None,
    discovered: bool | None = None,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        nickname=nickname,
        pokemon_name=pokemon_name,
        discovered=discovered,
        clean_cache=clean_cache,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[PokedexSchema] | list[PokedexSchema],
    status_code=HTTPStatus.OK,
)
async def list_pokedex(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokedexService, Depends(get_pokedex_service)],
    page_filter: Annotated[FilterPage, Depends(get_pokedex_filter)],
):
    return await service.list_all_cached(current_user, page_filter)


@router.get("/{name}", response_model=PokedexSchema, status_code=HTTPStatus.OK)
async def get_pokedex_detail(
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokedexService, Depends(get_pokedex_service)],
):
    return await service.find_detail(current_user, name)


@router.post(
    "/{name}/discover", response_model=PokedexSchema, status_code=HTTPStatus.OK
)
async def discover_pokedex(
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PokedexService, Depends(get_pokedex_service)],
):
    return await service.discover(current_user, name)
