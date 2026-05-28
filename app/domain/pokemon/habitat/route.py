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

from app.domain.pokemon.habitat.repository import HabitatRepository
from app.domain.pokemon.habitat.schema import HabitatSchema
from app.domain.pokemon.habitat.service import HabitatService

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_habitat_service(session: Session) -> HabitatService:
    return HabitatService(HabitatRepository(session))


Service = Annotated[HabitatService, Depends(get_habitat_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_habitat_filter(
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
    response_model=CustomLimitOffsetPage[HabitatSchema] | list[HabitatSchema],
    status_code=HTTPStatus.OK,
)
async def list_all(
    service: Service,
    current_user: CurrentUser,
    page_filter: Annotated[FilterPage, Depends(get_habitat_filter)] = None,
):
    return await service.list_all_cached(
        page_filter=page_filter,
        user_request=current_user.username,
    )


@router.get("/{param}", response_model=HabitatSchema, status_code=HTTPStatus.OK)
async def find_one(param: str, service: Service, current_user: CurrentUser):
    return await service.find_one_cached(
        param=param,
        user_request=current_user.username,
    )
