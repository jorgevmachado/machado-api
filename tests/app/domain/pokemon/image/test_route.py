from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.image.route import (
    find_one,
    get_image_filter,
    get_image_service,
    list_all,
)
from app.domain.pokemon.image.service import ImageService


class TestImageRoute:
    @staticmethod
    def test_get_image_service_builds_service() -> None:
        service = get_image_service(AsyncMock())

        assert isinstance(service, ImageService)

    @staticmethod
    def test_get_image_filter_builds_filter() -> None:
        page_filter = get_image_filter(page=1, limit=12, name="bulbasaur", order=1)

        assert page_filter.page == 1
        assert page_filter.limit == 12

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_delegates_to_service(
        image_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(items=[])
        page_filter = get_image_filter(page=1, limit=12)
        image_route_service.list_all_cached.return_value = expected

        result = await list_all(
            service=image_route_service,
            current_user=current_user,
            page_filter=page_filter,
        )

        assert result is expected
        image_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_delegates_to_service(
        image_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(order=1)
        image_route_service.find_one_cached.return_value = expected

        result = await find_one(
            param="1",
            service=image_route_service,
            current_user=current_user,
        )

        assert result is expected
        image_route_service.find_one_cached.assert_awaited_once_with(
            param="1",
            user_request="username",
        )
