from __future__ import annotations

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import CustomLimitOffsetPage
from app.core.security import get_current_trainer
from app.domain.trainer.pokedex.pokedex_entry.schema import PokedexEntrySchema
from app.models import Trainer

from app.shared.schemas import FilterPage

from app.domain.trainer.pokedex.repository import PokedexRepository
from app.domain.trainer.pokedex.service import PokedexService

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_pokedex_service(session: Session) -> PokedexService:
    return PokedexService(PokedexRepository(session))


Service = Annotated[PokedexService, Depends(get_pokedex_service)]
CurrentTrainer = Annotated[Trainer, Depends(get_current_trainer)]


def get_pokedex_filter(
    page: int | None = None,
    offset: int | None = None,
    limit: int | None = 12,
    clean_cache: bool = False,
) -> FilterPage:
    return FilterPage.build(
        page=page,
        offset=offset,
        limit=limit,
        clean_cache=clean_cache,
    )


@router.get(
    "",
    response_model=CustomLimitOffsetPage[PokedexEntrySchema] | list[PokedexEntrySchema],
    status_code=HTTPStatus.OK,
)
async def list_all_cached(
    service: Service,
    current_trainer: CurrentTrainer,
    page_filter: Annotated[FilterPage, Depends(get_pokedex_filter)] = None,
):
    return await service.list_all_cached(
        page_filter=FilterPage.build(page_filter, trainer_id=current_trainer.id),
        user_request=current_trainer.user.username,
    )


@router.get("/{param}", response_model=PokedexEntrySchema, status_code=HTTPStatus.OK)
async def find_one(
    param: str,
    service: Service,
    current_trainer: CurrentTrainer,
    clean_cache: bool = False,
):
    return await service.find_one_cached(
        param=param,
        trainer_id=current_trainer.id,
        user_request=current_trainer.user.username,
        clean_cache=clean_cache,
    )


@router.post(
    "/{name}/discover", response_model=PokedexEntrySchema, status_code=HTTPStatus.OK
)
async def discover(name: str, service: Service, current_trainer: CurrentTrainer):
    return await service.discover(name=name, trainer_id=current_trainer.id)
