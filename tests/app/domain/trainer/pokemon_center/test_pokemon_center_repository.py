from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.pagination import CustomLimitOffsetPage
from app.domain.trainer.pokemon_center.repository import PokemonCenterRepository
from app.shared.schemas import FilterPage


class FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


@pytest.mark.asyncio
async def test_create_summary_flushes_and_refreshes_entity():
    session = AsyncMock()
    session.add = Mock()
    repository = PokemonCenterRepository(session)
    entity = SimpleNamespace(id=uuid4())

    result = await repository.create_summary(entity)

    assert result is entity
    session.add.assert_called_once_with(entity)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(entity)


@pytest.mark.asyncio
async def test_create_logs_flushes_entities():
    session = AsyncMock()
    session.add_all = Mock()
    repository = PokemonCenterRepository(session)
    entities = [SimpleNamespace(id=uuid4())]

    result = await repository.create_logs(entities)

    assert result == entities
    session.add_all.assert_called_once_with(entities)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_latest_by_trainer_id_delegates_to_scalar():
    session = AsyncMock()
    expected = SimpleNamespace(id=uuid4())
    session.scalar = AsyncMock(return_value=expected)
    repository = PokemonCenterRepository(session)

    result = await repository.find_latest_by_trainer_id(uuid4())

    assert result is expected
    session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_history_returns_all_when_not_paginated():
    session = AsyncMock()
    items = [SimpleNamespace(id=uuid4())]
    session.scalars = AsyncMock(return_value=FakeScalarResult(items))
    repository = PokemonCenterRepository(session)

    result = await repository.list_history(trainer_id=uuid4(), page_filter=None)

    assert result == items
    session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_history_returns_custom_page_when_paginated():
    session = AsyncMock()
    items = [SimpleNamespace(id=uuid4())]
    session.scalar = AsyncMock(return_value=1)
    session.scalars = AsyncMock(return_value=FakeScalarResult(items))
    repository = PokemonCenterRepository(session)
    page_filter = FilterPage.build(page=1, limit=10)

    result = await repository.list_history(trainer_id=uuid4(), page_filter=page_filter)

    assert isinstance(result, CustomLimitOffsetPage)
    assert result.meta.total == 1
    assert result.items == items
    assert session.scalar.await_count == 1
    assert session.scalars.await_count == 1
