from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.encounter.route import (
    find_one,
    get_encounter_filter,
    get_encounter_service,
    list_all,
)
from app.domain.pokemon.encounter.service import EncounterService


class TestEncounterRoute:
    @staticmethod
    def test_get_encounter_service_builds_service() -> None:
        service = get_encounter_service(AsyncMock())

        assert isinstance(service, EncounterService)

    @staticmethod
    def test_get_encounter_filter_builds_filter() -> None:
        page_filter = get_encounter_filter(page=1, limit=12, name="route-1", order=1)

        assert page_filter.page == 1
        assert page_filter.limit == 12

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_all_delegates_to_service(
        encounter_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(items=[])
        page_filter = get_encounter_filter(page=1, limit=12)
        encounter_route_service.list_all_cached.return_value = expected

        result = await list_all(
            service=encounter_route_service,
            current_user=current_user,
            page_filter=page_filter,
        )

        assert result is expected
        encounter_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_find_one_delegates_to_service(
        encounter_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(name="route-1")
        encounter_route_service.find_one_cached.return_value = expected

        result = await find_one(
            param="route-1",
            service=encounter_route_service,
            current_user=current_user,
        )

        assert result is expected
        encounter_route_service.find_one_cached.assert_awaited_once_with(
            param="route-1",
            user_request="username",
        )
