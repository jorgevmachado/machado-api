from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security.security import get_current_trainer
from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.pokedex.schema import PokedexSchema
from app.domain.trainer.pokedex.service import PokedexService
from app.models import Trainer
from app.shared.schemas import FilterPage

router = APIRouter()

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
        current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
        service: Annotated[PokedexService, Depends(get_pokedex_service)],
        page_filter: Annotated[FilterPage, Depends(get_pokedex_filter)],
):
    return await service.list_all_cached(page_filter=page_filter, trainer_id=str(current_trainer.id))


@router.get("/{param}", response_model=PokedexSchema, status_code=HTTPStatus.OK)
async def get_pokedex_detail(
        param: str,
        current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
        service: Annotated[PokedexService, Depends(get_pokedex_service)],
):
    return await service.find_one_cached(param=param, trainer_id=str(current_trainer.id))


@router.post(
    "/{name}/discover", response_model=PokedexSchema, status_code=HTTPStatus.OK
)
async def discover_pokedex(
        name: str,
        current_trainer: Annotated[Trainer, Depends(get_current_trainer)],
        service: Annotated[PokedexService, Depends(get_pokedex_service)],
):
    return await service.discover(trainer=current_trainer, pokemon_name=name)
