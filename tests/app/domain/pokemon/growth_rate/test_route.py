from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.growth_rate.route import (
    find_one,
    get_growth_rate_filter,
    get_growth_rate_service,
    list_all,
)
from app.domain.pokemon.growth_rate.service import GrowthRateService


class TestGrowthRateRoute:
    @staticmethod
    def test_get_growth_rate_service_builds_service() -> None:
        service = get_growth_rate_service(AsyncMock())

        assert isinstance(service, GrowthRateService)

    @staticmethod
    def test_get_growth_rate_filter_builds_filter() -> None:
        page_filter = get_growth_rate_filter(page=1, limit=12, name="medium", order=1)

        assert page_filter.page == 1
        assert page_filter.limit == 12

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_delegates_to_service(
        growth_rate_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(items=[])
        page_filter = get_growth_rate_filter(page=1, limit=12)
        growth_rate_route_service.list_all_cached.return_value = expected

        result = await list_all(
            service=growth_rate_route_service,
            current_user=current_user,
            page_filter=page_filter,
        )

        assert result is expected
        growth_rate_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_delegates_to_service(
        growth_rate_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(name="medium")
        growth_rate_route_service.find_one_cached.return_value = expected

        result = await find_one(
            param="medium",
            service=growth_rate_route_service,
            current_user=current_user,
        )

        assert result is expected
        growth_rate_route_service.find_one_cached.assert_awaited_once_with(
            param="medium",
            user_request="username",
        )
