from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.service.base import BaseService
from app.domain.pokemon.route import (
    get_pokemon,
    get_pokemon_filter,
    get_pokemon_service,
    list_pokemons,
)
from app.domain.pokemon.service import PokemonService


def test_get_pokemon_service_builds_service():
    service = get_pokemon_service(AsyncMock())

    assert isinstance(service, PokemonService)
    assert isinstance(service, BaseService)


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
async def test_list_pokemons_delegates_to_service():
    service = AsyncMock()
    page_filter = get_pokemon_filter(page=1, limit=12)
    expected = SimpleNamespace(items=[])
    service.list_all_cached.return_value = expected

    result = await list_pokemons(
        _=SimpleNamespace(id="user-id"),
        service=service,
        page_filter=page_filter,
    )

    assert result is expected
    service.list_all_cached.assert_awaited_once_with(page_filter=page_filter)


@pytest.mark.asyncio
async def test_list_pokemons_passes_pagination_and_filters_to_service():
    service = AsyncMock()
    page_filter = get_pokemon_filter(page=2, limit=24, name="saur", type="grass")
    service.list_all_cached.return_value = SimpleNamespace(items=[])

    await list_pokemons(
        _=SimpleNamespace(id="user-id"),
        service=service,
        page_filter=page_filter,
    )

    service.list_all_cached.assert_awaited_once_with(page_filter=page_filter)


@pytest.mark.asyncio
async def test_get_pokemon_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(name="bulbasaur")
    service.find_detail.return_value = expected

    result = await get_pokemon(
        identifier="bulbasaur",
        _=SimpleNamespace(id="user-id"),
        service=service,
    )

    assert result is expected
    service.find_detail.assert_awaited_once_with("bulbasaur")
