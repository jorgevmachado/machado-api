from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.battle.battle_log.service import BattleLogService
from app.models.enums import BattleActorEnum, BattleLogTypeEnum


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.save = AsyncMock()
    return repository


def test_from_session_builds_service():
    service = BattleLogService.from_session(AsyncMock())
    assert isinstance(service, BattleLogService)


@pytest.mark.asyncio
async def test_start_saves_session_started_log(trainer_session: AsyncMock):
    repository = _build_repository(trainer_session)
    battle_session_id = uuid4()
    payload = {
        "pokemon_name": "charmander",
        "exploration_event_id": str(uuid4()),
        "trainer_active_owned_pokemon_id": str(uuid4()),
    }
    saved = object()
    repository.save.return_value = saved

    service = BattleLogService(repository=repository)
    result = await service.start(battle_session_id=battle_session_id, payload=payload)

    assert result is saved
    repository.save.assert_awaited_once()
    entity = repository.save.await_args.kwargs["entity"]
    assert entity.battle_session_id == battle_session_id
    assert entity.log_type == BattleLogTypeEnum.SESSION_STARTED
    assert entity.actor == BattleActorEnum.TRAINER
    assert entity.payload == payload
    assert "charmander" in entity.message
