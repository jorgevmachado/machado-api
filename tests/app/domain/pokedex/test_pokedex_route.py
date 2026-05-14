from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokedex.route import (
    discover_pokedex,
    get_pokedex_detail,
    get_pokedex_filter,
    get_pokedex_service,
    list_pokedex,
)
from app.domain.pokedex.service import PokedexService


def test_get_pokedex_service_builds_service():
    service = get_pokedex_service(AsyncMock())

    assert isinstance(service, PokedexService)


def test_get_pokedex_filter_builds_dynamic_filter():
    page_filter = get_pokedex_filter(
        page=1,
        limit=12,
        nickname="leaf",
        pokemon_name="bulbasaur",
        discovered=True,
    )

    assert page_filter.page == 1
    assert page_filter.limit == 12
    assert page_filter.nickname == "leaf"
    assert page_filter.pokemon_name == "bulbasaur"
    assert page_filter.discovered is True


@pytest.mark.asyncio
async def test_list_pokedex_delegates_to_service():
    service = AsyncMock()
    page_filter = get_pokedex_filter(page=1, limit=12)
    expected = SimpleNamespace(items=[])
    service.list_all_cached.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await list_pokedex(
        current_user=current_user,
        service=service,
        page_filter=page_filter,
    )

    assert result is expected
    service.list_all_cached.assert_awaited_once_with(current_user, page_filter)


@pytest.mark.asyncio
async def test_get_pokedex_detail_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="1")
    service.find_detail.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await get_pokedex_detail(
        "bulbasaur", current_user=current_user, service=service
    )

    assert result is expected
    service.find_detail.assert_awaited_once_with(current_user, "bulbasaur")


@pytest.mark.asyncio
async def test_discover_pokedex_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="1", discovered=True)
    service.discover.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await discover_pokedex(
        "bulbasaur", current_user=current_user, service=service
    )

    assert result is expected
    service.discover.assert_awaited_once_with(current_user, "bulbasaur")
