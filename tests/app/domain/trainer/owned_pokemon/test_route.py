from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.owned_pokemon.route import (
    find_one,
    get_owned_pokemon_filter,
    get_owned_pokemon_service,
    list_all,
)
from app.domain.trainer.owned_pokemon.service import OwnedPokemonService


def test_get_owned_pokemon_service_builds_service() -> None:
    service = get_owned_pokemon_service(AsyncMock())
    assert isinstance(service, OwnedPokemonService)


def test_get_owned_pokemon_filter_builds_filter() -> None:
    page_filter = get_owned_pokemon_filter(page=1, offset=1, limit=12, name="poke", order=2)
    assert page_filter.page == 1
    assert page_filter.offset == 1
    assert page_filter.limit == 12
    assert page_filter.name == "poke"
    assert page_filter.order == 2


@pytest.mark.asyncio
async def test_list_all_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    service = AsyncMock()
    service.list_all_cached.return_value = SimpleNamespace(items=[])
    page_filter = get_owned_pokemon_filter(page=1, limit=12)

    await list_all(service=service, current_trainer=current_trainer, page_filter=page_filter)

    args = service.list_all_cached.await_args.kwargs
    assert args["page_filter"].trainer_id == current_trainer.id
    assert args["user_request"] == "ash"


@pytest.mark.asyncio
async def test_find_one_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    service = AsyncMock()
    expected = SimpleNamespace(id="owned")
    service.find_one_cached.return_value = expected

    result = await find_one(param="owned", service=service, current_trainer=current_trainer)

    assert result is expected
    service.find_one_cached.assert_awaited_once_with(
        param="owned",
        trainer_id=current_trainer.id,
        user_request="ash",
    )
