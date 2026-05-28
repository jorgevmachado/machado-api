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

from app.domain.pokemon.ability.repository import AbilityRepository
from app.domain.pokemon.ability.schema import AbilitySchema
from app.domain.pokemon.ability.service import AbilityService

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get_ability_service(session: Session) -> AbilityService:
    return AbilityService(AbilityRepository(session))


Service = Annotated[AbilityService, Depends(get_ability_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_ability_filter(
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
    response_model=CustomLimitOffsetPage[AbilitySchema] | list[AbilitySchema],
    status_code=HTTPStatus.OK,
)
async def list_all(
    service: Service,
    current_user: CurrentUser,
    page_filter: Annotated[FilterPage, Depends(get_ability_filter)] = None,
):
    return await service.list_all_cached(
        page_filter=page_filter,
        user_request=current_user.username,
    )


@router.get("/{param}", response_model=AbilitySchema, status_code=HTTPStatus.OK)
async def find_one(
    param: str,
    service: Service,
    current_user: CurrentUser,
    clean_cache: bool = False,
):
    return await service.find_one_cached(
        param=param,
        clean_cache=clean_cache,
        user_request=current_user.username,
    )
