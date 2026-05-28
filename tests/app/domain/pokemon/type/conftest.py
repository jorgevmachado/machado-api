from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.pokemon.type.schema import TypeSyncResourceSchema


@pytest.fixture
def current_user() -> SimpleNamespace:
    return SimpleNamespace(id="user-id", username="username")


@pytest.fixture
def type_route_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def type_repository_mock() -> AsyncMock:
    repository = AsyncMock()
    repository.find_by = AsyncMock(return_value=None)
    repository.save = AsyncMock()
    repository.update = AsyncMock()
    return repository


@pytest.fixture
def type_entity() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name="grass",
        url="https://pokeapi.co/api/v2/type/12/",
        order=12,
        status="INCOMPLETE",
        strengths=[],
        weaknesses=[],
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
    )


@pytest.fixture
def type_sync_resource(type_entity: SimpleNamespace) -> TypeSyncResourceSchema:
    return TypeSyncResourceSchema(
        type=type_entity, type_weaknesses=[], type_strengths=[]
    )
