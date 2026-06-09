from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.type.route import (
    find_one,
    get_type_filter,
    get_type_service,
    list_all,
)
from app.domain.pokemon.type.service import TypeService


class TestTypeRoute:
    @staticmethod
    def test_get_type_service_builds_service() -> None:
        service = get_type_service(AsyncMock())

        assert isinstance(service, TypeService)

    @staticmethod
    def test_get_type_filter_builds_filter() -> None:
        page_filter = get_type_filter(page=1, limit=12, name="grass", order=12)

        assert page_filter.page == 1
        assert page_filter.limit == 12

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_delegates_to_service(
        type_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(items=[])
        page_filter = get_type_filter(page=1, limit=12)
        type_route_service.list_all_cached.return_value = expected

        result = await list_all(
            service=type_route_service,
            current_user=current_user,
            page_filter=page_filter,
        )

        assert result is expected
        type_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_delegates_to_service(
        type_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(name="grass")
        type_route_service.find_one_cached.return_value = expected

        result = await find_one(
            param="grass",
            service=type_route_service,
            current_user=current_user,
        )

        assert result is expected
        type_route_service.find_one_cached.assert_awaited_once_with(
            param="grass",
            user_request="username",
        )
