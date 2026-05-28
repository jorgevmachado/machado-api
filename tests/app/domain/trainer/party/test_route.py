from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.party.route import (
    find_one,
    get_party_filter,
    get_party_service,
    list_all,
)
from app.domain.trainer.party.service import TrainerPartyService


def test_get_party_service_builds_service() -> None:
    service = get_party_service(AsyncMock())
    assert isinstance(service, TrainerPartyService)


def test_get_party_filter_builds_filter() -> None:
    page_filter = get_party_filter(page=1, offset=2, limit=6, clean_cache=True)
    assert page_filter.page == 1
    assert page_filter.offset == 2
    assert page_filter.limit == 6
    assert page_filter.clean_cache is True


@pytest.mark.asyncio
async def test_list_all_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    service = AsyncMock()
    service.list_all_cached.return_value = SimpleNamespace(items=[])
    page_filter = get_party_filter(page=1, limit=6)

    await list_all(
        service=service,
        current_trainer=current_trainer,
        page_filter=page_filter,
    )

    args = service.list_all_cached.await_args.kwargs
    assert args["page_filter"].trainer_id == current_trainer.id
    assert args["user_request"] == "ash"


@pytest.mark.asyncio
async def test_find_one_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    expected = SimpleNamespace(id=uuid4())
    service = AsyncMock()
    service.find_one_cached.return_value = expected

    result = await find_one(
        param="party",
        service=service,
        current_trainer=current_trainer,
    )

    assert result is expected
    service.find_one_cached.assert_awaited_once_with(
        param="party",
        trainer_id=current_trainer.id,
        user_request="ash",
    )
