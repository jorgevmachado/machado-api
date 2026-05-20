from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.my_pokemon import (
    create_my_pokemon,
    get_my_pokemon_filter,
    get_my_pokemon_service,
    list_my_pokemon,
    get_my_pokemon,
)
from app.domain.trainer.my_pokemon import CreateMyPokemonSchema
from app.domain.trainer.my_pokemon import MyPokemonService


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
    current_trainer = SimpleNamespace(id="trainer-id")

    result = await create_my_pokemon(
        payload, current_trainer=current_trainer, service=service
    )

    assert result is expected
    service.create.assert_awaited_once_with(trainer=current_trainer, payload=payload)


@pytest.mark.asyncio
async def test_list_my_pokemon_delegates_to_service():
    service = AsyncMock()
    page_filter = get_my_pokemon_filter(page=1, limit=12)
    expected = []
    service.list_all_cached.return_value = expected
    current_trainer = SimpleNamespace(id=uuid4())

    result = await list_my_pokemon(
        current_trainer=current_trainer,
        service=service,
        page_filter=page_filter,
    )

    assert result == expected
    service.list_all_cached.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_my_pokemon_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="1", name="pikachu")
    service.find_one.return_value = expected
    current_trainer = SimpleNamespace(id=uuid4())

    result = await get_my_pokemon(
        name="pikachu",
        current_trainer=current_trainer,
        service=service,
    )

    assert result == expected
    service.find_one.assert_awaited_once()
