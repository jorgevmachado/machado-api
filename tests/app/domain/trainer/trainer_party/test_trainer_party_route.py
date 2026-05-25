from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.trainer_party import (
    get_trainer_party,
    get_trainer_party_service,
    update_trainer_party,
)
from app.domain.trainer.trainer_party import TrainerPartyService, UpdateTrainerPartySchema


def test_get_trainer_party_service_builds_service():
    service = get_trainer_party_service(AsyncMock())

    assert isinstance(service, TrainerPartyService)


@pytest.mark.asyncio
async def test_get_trainer_party_delegates_to_service():
    service = AsyncMock()
    expected = [SimpleNamespace(id="party-1")]
    service.get_party.return_value = expected
    current_trainer = SimpleNamespace(id="user-id")

    result = await get_trainer_party(current_trainer=current_trainer, service=service)

    assert result is expected
    service.get_party.assert_awaited_once_with(trainer=current_trainer)


@pytest.mark.asyncio
async def test_update_trainer_party_delegates_to_service():
    service = AsyncMock()
    expected = [SimpleNamespace(id="party-1")]
    service.update_party.return_value = expected
    current_trainer = SimpleNamespace(id="user-id")
    payload = UpdateTrainerPartySchema(my_pokemon_ids=[uuid4()])

    result = await update_trainer_party(
        payload,
        current_trainer=current_trainer,
        service=service,
    )

    assert result is expected
    service.update_party.assert_awaited_once_with(trainer=current_trainer, payload=payload)
