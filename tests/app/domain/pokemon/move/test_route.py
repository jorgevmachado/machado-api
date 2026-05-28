from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.move.route import (
    find_one,
    get_move_filter,
    get_move_service,
    list_all,
)
from app.domain.pokemon.move.service import MoveService


class TestMoveRoute:
    def test_get_move_service_builds_service(self) -> None:
        service = get_move_service(AsyncMock())

        assert isinstance(service, MoveService)

    def test_get_move_filter_builds_filter(self) -> None:
        page_filter = get_move_filter(page=1, limit=12, name="tackle", order=33)

        assert page_filter.page == 1
        assert page_filter.limit == 12

    @pytest.mark.asyncio
    async def test_list_all_delegates_to_service(
        self,
        move_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(items=[])
        page_filter = get_move_filter(page=1, limit=12)
        move_route_service.list_all_cached.return_value = expected

        result = await list_all(
            service=move_route_service,
            current_user=current_user,
            page_filter=page_filter,
        )

        assert result is expected
        move_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @pytest.mark.asyncio
    async def test_find_one_delegates_to_service(
        self,
        move_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(name="tackle")
        move_route_service.find_one_cached.return_value = expected

        result = await find_one(
            param="tackle",
            service=move_route_service,
            current_user=current_user,
        )

        assert result is expected
        move_route_service.find_one_cached.assert_awaited_once_with(
            param="tackle",
            user_request="username",
        )
