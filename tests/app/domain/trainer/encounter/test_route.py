from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.encounter.route import (
    find_one,
    get_encounter_filter,
    get_trainer_encounter_service,
    list_all,
    select_active,
)
from app.domain.trainer.encounter.schema import ActiveTrainerEncounterPayloadSchema
from app.domain.trainer.encounter.service import TrainerEncounterService


def test_get_trainer_encounter_service_builds_service() -> None:
    service = get_trainer_encounter_service(AsyncMock())
    assert isinstance(service, TrainerEncounterService)


def test_get_encounter_filter_builds_filter() -> None:
    page_filter = get_encounter_filter(page=1, offset=1, limit=10)
    assert page_filter.page == 1
    assert page_filter.offset == 1
    assert page_filter.limit == 10


@pytest.mark.asyncio
async def test_list_all_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    service = AsyncMock()
    service.list_all_cached.return_value = SimpleNamespace(items=[])
    page_filter = get_encounter_filter(page=1, limit=12)

    await list_all(
        service=service, current_trainer=current_trainer, page_filter=page_filter
    )

    args = service.list_all_cached.await_args.kwargs
    assert args["page_filter"].trainer_id == current_trainer.id
    assert args["user_request"] == "ash"


@pytest.mark.asyncio
async def test_find_one_delegates_to_service(current_trainer: SimpleNamespace) -> None:
    service = AsyncMock()
    expected = SimpleNamespace(id="encounter")
    service.find_one_cached.return_value = expected

    result = await find_one(
        param="encounter", service=service, current_trainer=current_trainer
    )

    assert result is expected
    service.find_one_cached.assert_awaited_once_with(
        param="encounter",
        user_request="ash",
        trainer_id=current_trainer.id,
    )


@pytest.mark.asyncio
async def test_select_active(current_trainer: SimpleNamespace) -> None:
    payload = ActiveTrainerEncounterPayloadSchema(encounter_id="encounter-id")
    trainer_encounter = SimpleNamespace(id="encounter-id", is_active=True)
    service = AsyncMock()
    service.select_active.return_value = trainer_encounter

    result = await select_active(
        payload=payload, service=service, current_trainer=current_trainer
    )

    assert result is trainer_encounter

    service.select_active.assert_awaited_once_with(
        trainer=current_trainer,
        encounter_id=payload.encounter_id,
    )
