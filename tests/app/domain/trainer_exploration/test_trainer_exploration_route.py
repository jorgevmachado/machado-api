from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.trainer_exploration import (
    get_trainer_exploration_service,
    get_trainer_home,
    list_trainer_encounters,
    select_active_trainer_encounter,
    update_trainer_party,
    walk_trainer_encounter,
)
from app.domain.trainer.trainer_exploration import (
    SelectTrainerEncounterSchema,
    UpdateTrainerPartySchema,
)
from app.domain.trainer.trainer_exploration import TrainerExplorationService


def test_get_trainer_exploration_service_builds_service():
    service = get_trainer_exploration_service(AsyncMock())

    assert isinstance(service, TrainerExplorationService)


@pytest.mark.asyncio
async def test_get_trainer_home_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(trainer=SimpleNamespace(id="trainer-1"))
    service.get_home.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await get_trainer_home(current_user=current_user, service=service)

    assert result is expected
    service.get_home.assert_awaited_once_with(current_user)


@pytest.mark.asyncio
async def test_list_trainer_encounters_delegates_to_service():
    service = AsyncMock()
    expected = [SimpleNamespace(id="encounter-1")]
    service.list_encounters.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await list_trainer_encounters(current_user=current_user, service=service)

    assert result is expected
    service.list_encounters.assert_awaited_once_with(current_user)


@pytest.mark.asyncio
async def test_select_active_trainer_encounter_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="encounter-1", is_active=True)
    service.select_active_encounter.return_value = expected
    current_user = SimpleNamespace(id="user-id")
    payload = SelectTrainerEncounterSchema(encounter_id=uuid4())

    result = await select_active_trainer_encounter(
        payload,
        current_user=current_user,
        service=service,
    )

    assert result is expected
    service.select_active_encounter.assert_awaited_once_with(current_user, payload)


@pytest.mark.asyncio
async def test_update_trainer_party_delegates_to_service():
    service = AsyncMock()
    expected = [SimpleNamespace(id="party-1")]
    service.update_party.return_value = expected
    current_user = SimpleNamespace(id="user-id")
    payload = UpdateTrainerPartySchema(my_pokemon_ids=[uuid4()])

    result = await update_trainer_party(
        payload,
        current_user=current_user,
        service=service,
    )

    assert result is expected
    service.update_party.assert_awaited_once_with(current_user, payload)


@pytest.mark.asyncio
async def test_walk_trainer_encounter_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="event-1")
    service.walk.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await walk_trainer_encounter(current_user=current_user, service=service)

    assert result is expected
    service.walk.assert_awaited_once_with(current_user)
