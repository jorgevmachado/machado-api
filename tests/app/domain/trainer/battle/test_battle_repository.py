from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.trainer.battle.repository import (
    BattleSessionRepository,
)


class ScalarsResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


@pytest.mark.asyncio
async def test_repository_query_and_create_methods_delegate_to_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.scalar.return_value = 'session'
    session.scalars.return_value = ScalarsResult(['log'])
    repository = BattleSessionRepository(session)

    assert await repository.find_active_by_trainer_id(uuid4()) == 'session'
    assert await repository.find_by_id_and_trainer_id(uuid4(), uuid4()) == 'session'
    assert await repository.find_latest_by_trainer_id(uuid4()) == 'session'

    entity = SimpleNamespace()
    assert await repository.create_session(entity) is entity
    assert await repository.create_turn(entity) is entity
    assert await repository.create_log(entity) is entity
    assert await repository.list_logs(uuid4()) == ['log']
    assert await repository.list_turns(uuid4()) == ['log']
    assert await repository.list_available_party_members(uuid4()) == ['log']

    assert session.add.call_count == 3
    assert session.flush.await_count == 3
