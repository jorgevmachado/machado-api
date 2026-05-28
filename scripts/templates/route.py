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

from app.domain.__DOMAIN_MODULE__.repository import __CLASS_NAME__Repository
from app.domain.__DOMAIN_MODULE__.schema import __CLASS_NAME__Schema
from app.domain.__DOMAIN_MODULE__.service import __CLASS_NAME__Service

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]


def get___DOMAIN_ENTITY___service(session: Session) -> __CLASS_NAME__Service:
    return __CLASS_NAME__Service(__CLASS_NAME__Repository(session))


Service = Annotated[__CLASS_NAME__Service, Depends(get___DOMAIN_ENTITY___service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get___DOMAIN_ENTITY___filter(
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
    response_model=CustomLimitOffsetPage[__CLASS_NAME__Schema]
    | list[__CLASS_NAME__Schema],
    status_code=HTTPStatus.OK,
)
async def list_all(
    service: Service,
    current_user: CurrentUser,
    page_filter: Annotated[FilterPage, Depends(get___DOMAIN_ENTITY___filter)] = None,
):
    return await service.list_all_cached(
        page_filter=page_filter,
        user_request=current_user.username,
    )


@router.get("/{param}", response_model=__CLASS_NAME__Schema, status_code=HTTPStatus.OK)
async def find_one(param: str, service: Service, current_user: CurrentUser):
    return await service.find_one_cached(
        param=param,
        user_request=current_user.username,
    )
