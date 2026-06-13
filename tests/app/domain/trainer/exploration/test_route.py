from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.exploration.route import (
    find_one,
    get_exploration_filter,
    get_exploration_service,
    list_all,
)
from app.domain.trainer.exploration.service import ExplorationService


def test_get_exploration_service_builds_service():
    service = get_exploration_service(AsyncMock())
    assert isinstance(service, ExplorationService)


def test_get_exploration_filter_builds_filter():
    page_filter = get_exploration_filter(page=1, offset=0, limit=8, clean_cache=True)
    assert page_filter.page == 1
    assert page_filter.limit == 8
    assert page_filter.clean_cache is True


@pytest.mark.asyncio
async def test_list_all_delegates_to_service():
    service = AsyncMock()
    service.list_all_cached.return_value = []
    current_user = SimpleNamespace(username="ash")
    page_filter = get_exploration_filter(limit=12)

    await list_all(service=service, current_user=current_user, page_filter=page_filter)

    service.list_all_cached.assert_awaited_once()
    kwargs = service.list_all_cached.await_args.kwargs
    assert kwargs["user_request"] == "ash"


@pytest.mark.asyncio
async def test_find_one_delegates_to_service():
    expected = SimpleNamespace(id=uuid4())
    service = AsyncMock()
    service.find_one_cached.return_value = expected
    current_user = SimpleNamespace(username="ash")

    result = await find_one(
        param="event-id", service=service, current_user=current_user
    )

    assert result is expected
    service.find_one_cached.assert_awaited_once_with(
        param="event-id",
        user_request="ash",
    )
