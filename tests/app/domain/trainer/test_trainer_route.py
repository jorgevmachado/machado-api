from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.route import get_trainer_service, onboarding
from app.domain.trainer.schema import OnboardPayloadSchema
from app.domain.trainer.service import TrainerService


def test_get_trainer_service_builds_service() -> None:
    service = get_trainer_service(AsyncMock())
    assert isinstance(service, TrainerService)


@pytest.mark.asyncio
async def test_onboarding_delegates_to_service(current_user: SimpleNamespace) -> None:
    payload = OnboardPayloadSchema(pokemon_name="bulbasaur")
    service = AsyncMock()
    expected = SimpleNamespace(id="trainer-id")
    service.onboard.return_value = expected

    result = await onboarding(payload=payload, service=service, current_user=current_user)

    assert result is expected
    service.onboard.assert_awaited_once_with(current_user=current_user, payload=payload)
