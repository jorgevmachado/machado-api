from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.trainer_log.route import (
    find_one,
    get_trainer_log_service,
    get_trainer_log_filter,
    list_all,
)
from app.domain.trainer.trainer_log.service import TrainerLogService


def test_get_trainer_log_service_builds_service() -> None:
    service = get_trainer_log_service(AsyncMock())
    assert isinstance(service, TrainerLogService)


def test_get_trainer_log_filter_builds_filter_page() -> None:
    page_filter = get_trainer_log_filter(
        page=2,
        offset=24,
        limit=10,
        name="ash",
        order=1,
        clean_cache=True,
    )

    assert page_filter.page == 2
    assert page_filter.offset == 24
    assert page_filter.limit == 10
    assert page_filter.name == "ash"
    assert page_filter.order == 1
    assert page_filter.clean_cache is True


@pytest.mark.asyncio
async def test_list_all_delegates_to_service() -> None:
    expected = [SimpleNamespace(id="log-1")]
    service = AsyncMock()
    service.list_all_cached = AsyncMock(return_value=expected)
    current_user = SimpleNamespace(username="ash")
    page_filter = SimpleNamespace()

    result = await list_all(
        service=service,
        current_user=current_user,
        page_filter=page_filter,
    )

    assert result is expected
    service.list_all_cached.assert_awaited_once_with(
        page_filter=page_filter,
        user_request="ash",
    )


@pytest.mark.asyncio
async def test_find_one_delegates_to_service() -> None:
    expected = SimpleNamespace(id="log-1")
    service = AsyncMock()
    service.find_one_cached = AsyncMock(return_value=expected)
    current_user = SimpleNamespace(username="ash")

    result = await find_one(
        param="log-1",
        service=service,
        current_user=current_user,
    )

    assert result is expected
    service.find_one_cached.assert_awaited_once_with(
        param="log-1",
        user_request="ash",
    )
