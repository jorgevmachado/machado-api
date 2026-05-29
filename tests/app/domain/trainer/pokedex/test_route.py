from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.pokedex.route import (
    discover,
    find_one,
    get_pokedex_filter,
    get_pokedex_service,
    list_all_cached,
)
from app.domain.trainer.pokedex.service import PokedexService


def test_get_pokedex_service_builds_service() -> None:
    service = get_pokedex_service(AsyncMock())
    assert isinstance(service, PokedexService)


def test_get_pokedex_filter_builds_filter() -> None:
    page_filter = get_pokedex_filter(page=1, offset=1, limit=12, clean_cache=True)
    assert page_filter.page == 1
    assert page_filter.offset == 1
    assert page_filter.limit == 12
    assert page_filter.clean_cache is True


@pytest.mark.asyncio
async def test_list_all_cached_delegates_to_service(
    current_trainer: SimpleNamespace,
) -> None:
    service = AsyncMock()
    service.list_all_cached.return_value = SimpleNamespace(items=[])
    page_filter = get_pokedex_filter(page=1, limit=10)

    await list_all_cached(
        service=service, current_trainer=current_trainer, page_filter=page_filter
    )

    args = service.list_all_cached.await_args.kwargs
    assert args["page_filter"].trainer_id == current_trainer.id
    assert args["user_request"] == "ash"


@pytest.mark.asyncio
async def test_find_one_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    service = AsyncMock()
    expected = SimpleNamespace(id="entry")
    service.find_one_cached.return_value = expected

    result = await find_one(
        param="entry", service=service, current_trainer=current_trainer
    )

    assert result is expected
    service.find_one_cached.assert_awaited_once_with(
        param="entry",
        trainer_id=current_trainer.id,
        user_request="ash",
        clean_cache=False,
    )


@pytest.mark.asyncio
async def test_discover_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    service = AsyncMock()
    expected = SimpleNamespace(id="entry", discovered=True)
    service.discover.return_value = expected

    result = await discover(
        name="bulbasaur", service=service, current_trainer=current_trainer
    )

    assert result is expected
    service.discover.assert_awaited_once_with(
        name="bulbasaur",
        trainer_id=current_trainer.id,
    )
