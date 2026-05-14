from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.route import (
    get_trainer_service,
    onboard_trainer,
)
from app.domain.trainer.schema import OnboardingTrainerSchema
from app.domain.trainer.service import TrainerService


def test_get_trainer_service_builds_service():
    service = get_trainer_service(AsyncMock())

    assert isinstance(service, TrainerService)


@pytest.mark.asyncio
async def test_onboard_trainer_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(id="1", name="bulbasaur")
    service.onboard.return_value = expected
    payload = OnboardingTrainerSchema(pokemon_name="bulbasaur")
    current_user = SimpleNamespace(id="user-id")

    result = await onboard_trainer(
        payload,
        current_user=current_user,
        service=service,
    )

    assert result is expected
    service.onboard.assert_awaited_once_with(current_user, payload)
