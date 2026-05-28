from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.shape.route import (
    find_one,
    get_shape_filter,
    get_shape_service,
    list_all,
)
from app.domain.pokemon.shape.service import ShapeService


class TestShapeRoute:
    @staticmethod
    def test_get_shape_service_builds_service() -> None:
        service = get_shape_service(AsyncMock())

        assert isinstance(service, ShapeService)

    @staticmethod
    def test_get_shape_filter_builds_filter() -> None:
        page_filter = get_shape_filter(page=1, limit=12, name="quadruped", order=1)

        assert page_filter.page == 1
        assert page_filter.limit == 12

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_delegates_to_service(
        shape_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(items=[])
        page_filter = get_shape_filter(page=1, limit=12)
        shape_route_service.list_all_cached.return_value = expected

        result = await list_all(
            service=shape_route_service,
            current_user=current_user,
            page_filter=page_filter,
        )

        assert result is expected
        shape_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_delegates_to_service(
        shape_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(name="quadruped")
        shape_route_service.find_one_cached.return_value = expected

        result = await find_one(
            param="quadruped",
            service=shape_route_service,
            current_user=current_user,
        )

        assert result is expected
        shape_route_service.find_one_cached.assert_awaited_once_with(
            param="quadruped",
            user_request="username",
        )
