from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def current_user() -> SimpleNamespace:
    return SimpleNamespace(id="user-id", username="username")


@pytest.fixture
def move_route_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def move_repository_mock() -> AsyncMock:
    repository = AsyncMock()
    repository.find_by = AsyncMock(return_value=None)
    repository.save = AsyncMock()
    return repository
