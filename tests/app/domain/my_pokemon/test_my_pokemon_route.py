from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.my_pokemon.route import (
    create_my_pokemon,
    get_my_pokemon,
    get_my_pokemon_filter,
    get_my_pokemon_service,
    list_my_pokemon,
)
from app.domain.my_pokemon.schema import CreateMyPokemonSchema
from app.domain.my_pokemon.service import MyPokemonService


def test_get_my_pokemon_service_builds_service():
    service = get_my_pokemon_service(AsyncMock())

    assert isinstance(service, MyPokemonService)


def test_get_my_pokemon_filter_builds_dynamic_filter():
    page_filter = get_my_pokemon_filter(
        page=1, limit=12, name="char", pokemon_name="charizard"
    )

    assert page_filter.page == 1
    assert page_filter.limit == 12
    assert page_filter.name == "char"
    assert page_filter.pokemon_name == "charizard"


@pytest.mark.asyncio
async def test_create_my_pokemon_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="1", name="bulbasaur")
    service.create.return_value = expected
    payload = CreateMyPokemonSchema(pokemon_name="bulbasaur")
    current_user = SimpleNamespace(id="user-id")

    result = await create_my_pokemon(
        payload, current_user=current_user, service=service
    )

    assert result is expected
    service.create.assert_awaited_once_with(current_user, payload)


@pytest.mark.asyncio
async def test_list_my_pokemon_delegates_to_service():
    service = AsyncMock()
    page_filter = get_my_pokemon_filter(page=1, limit=12)
    expected = SimpleNamespace(items=[])
    service.list_all_cached.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await list_my_pokemon(
        current_user=current_user,
        service=service,
        page_filter=page_filter,
    )

    assert result is expected
    service.list_all_cached.assert_awaited_once_with(current_user, page_filter)


@pytest.mark.asyncio
async def test_get_my_pokemon_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="1", name="bulbasaur")
    service.find_detail.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await get_my_pokemon(
        "bulbasaur", current_user=current_user, service=service
    )

    assert result is expected
    service.find_detail.assert_awaited_once_with(current_user, "bulbasaur")
