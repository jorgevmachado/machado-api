from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.service.base import BaseService
from app.domain.pokemon.route import (
    find_one,
    get_pokemon_filter,
    get_pokemon_service,
    list_all,
)
from app.domain.pokemon.service import PokemonService


class TestPokemonRouter:
    @staticmethod
    def test_get_pokemon_service_builds_service():
        service = get_pokemon_service(AsyncMock())

        assert isinstance(service, PokemonService)
        assert isinstance(service, BaseService)

    @staticmethod
    def test_get_pokemon_filter_builds_dynamic_filter():
        page_filter = get_pokemon_filter(
            page=1, limit=12, name="saur", order=1, status="INCOMPLETE", type="grass"
        )

        assert page_filter.page == 1
        assert page_filter.limit == 12
        assert page_filter.name == "saur"
        assert page_filter.order == 1
        assert page_filter.status == "INCOMPLETE"
        assert page_filter.type == "grass"

    @pytest.mark.asyncio
    @staticmethod
    async def test_list_all_delegates_to_service(
        pokemon_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        page_filter = get_pokemon_filter(page=1, limit=12)
        expected = SimpleNamespace(items=[])
        pokemon_route_service.list_all_cached.return_value = expected

        result = await list_all(
            current_user=current_user,
            service=pokemon_route_service,
            page_filter=page_filter,
        )

        assert result is expected
        pokemon_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @pytest.mark.asyncio
    @staticmethod
    async def test_list_all_passes_filter_and_pagination(
        pokemon_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        page_filter = get_pokemon_filter(page=2, limit=24, name="saur", type="grass")
        pokemon_route_service.list_all_cached.return_value = SimpleNamespace(items=[])

        await list_all(
            current_user=current_user,
            service=pokemon_route_service,
            page_filter=page_filter,
        )

        pokemon_route_service.list_all_cached.assert_awaited_once_with(
            page_filter=page_filter,
            user_request="username",
        )

    @pytest.mark.asyncio
    @staticmethod
    async def test_find_one_delegates_to_service(
        pokemon_route_service: AsyncMock,
        current_user: SimpleNamespace,
    ) -> None:
        expected = SimpleNamespace(name="bulbasaur")
        pokemon_route_service.find_one_cached.return_value = expected

        result = await find_one(
            param="bulbasaur",
            current_user=current_user,
            service=pokemon_route_service,
        )

        assert result is expected
        pokemon_route_service.find_one_cached.assert_awaited_once_with(
            param="bulbasaur",
            user_request="username",
            clean_cache=False,
        )
