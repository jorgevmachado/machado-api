from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models import RoleEnum


@pytest.fixture
def trainer_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def current_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        username="ash",
        role=RoleEnum.USER,
        trainer=None,
    )


@pytest.fixture
def current_trainer() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user=SimpleNamespace(username="ash"),
    )
