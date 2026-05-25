from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.encounter import (
    get_trainer_encounter_service,
    list_trainer_encounters,
    select_active_trainer_encounter,
    walk_trainer_encounter,
)
from app.domain.trainer.encounter import SelectTrainerEncounterSchema
from app.domain.trainer.encounter.route import get_trainer_encounter_filter, get_trainer_encounter
from app.domain.trainer.encounter import TrainerEncounterService
from app.shared.schemas import FilterPage


def test_get_trainer_encounter_service_builds_service():
    service = get_trainer_encounter_service(AsyncMock())

    assert isinstance(service, TrainerEncounterService)


def test_get_trainer_encounter_filter_builds_dynamic_filter():
    result = get_trainer_encounter_filter(
        page=2,
        offset=12,
        limit=6,
        is_active=True,
        clean_cache=True,
    )

    assert result.page == 2
    assert result.offset == 12
    assert result.limit == 6
    assert result.is_active is True
    assert result.clean_cache is True


@pytest.mark.asyncio
async def test_list_trainer_encounters_delegates_to_service():
    service = AsyncMock()
    expected = [SimpleNamespace(id="encounter-1")]
    service.list_all_cached.return_value = expected
    current_trainer = SimpleNamespace(id=uuid4())
    page_filter = FilterPage.build(page=1, limit=12, clean_cache=False)

    result = await list_trainer_encounters(
        current_trainer=current_trainer,
        service=service,
        page_filter=page_filter,
    )

    assert result is expected
    service.list_all_cached.assert_awaited_once()
    called_filter = service.list_all_cached.await_args.kwargs["page_filter"]
    assert called_filter.trainer_id == str(current_trainer.id)
    assert called_filter.page == page_filter.page
    assert called_filter.limit == page_filter.limit
    assert called_filter.clean_cache == page_filter.clean_cache

@pytest.mark.asyncio
async def test_get_trainer_encounter_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="encounter-1")
    service.find_one_cached.return_value = expected
    current_trainer = SimpleNamespace(id="user-id")
    encounter_id = "encounter-1"

    result = await get_trainer_encounter(
        encounter_id,
        current_trainer=current_trainer,
        service=service,
    )

    assert result is expected
    service.find_one_cached.assert_awaited_once_with(
        param=encounter_id,
        trainer_id=current_trainer.id
    )

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
async def test_walk_trainer_encounter_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="event-1")
    service.walk.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await walk_trainer_encounter(current_user=current_user, service=service)

    assert result is expected
    service.walk.assert_awaited_once_with(current_user)
