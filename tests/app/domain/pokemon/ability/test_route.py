from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.ability.route import (
    find_one,
    get_ability_filter,
    get_ability_service,
    list_all,
)
from app.domain.pokemon.ability.service import AbilityService


class TestAbilityRoute:
    def test_get_ability_service_builds_service(self) -> None:
        service = get_ability_service(AsyncMock())

        assert isinstance(service, AbilityService)

    def test_get_ability_filter_builds_filter(self) -> None:
        page_filter = get_ability_filter(page=1, limit=12, name="overgrow", order=3)

        assert page_filter.page == 1
        assert page_filter.limit == 12

    @pytest.mark.asyncio
    async def test_list_all_delegates_to_service(
        self,
        ability_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(items=[])
        page_filter = get_ability_filter(page=1, limit=12)
        ability_route_service.list_all_cached.return_value = expected

        result = await list_all(
            service=ability_route_service,
            current_user=current_user,
            page_filter=page_filter,
        )

        assert result is expected
        ability_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @pytest.mark.asyncio
    async def test_find_one_delegates_to_service(
        self,
        ability_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        ability = SimpleNamespace(name="overgrow")
        ability_route_service.find_one_cached.return_value = ability

        result = await find_one(
            param="overgrow",
            service=ability_route_service,
            current_user=current_user,
            clean_cache=True,
        )

        assert result is ability
        ability_route_service.find_one_cached.assert_awaited_once_with(
            param="overgrow",
            clean_cache=True,
            user_request="username",
        )
