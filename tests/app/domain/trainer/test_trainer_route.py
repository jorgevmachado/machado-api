from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.route import (
    capture,
    explore,
    fight,
    get_trainer_service,
    onboarding,
)
from app.domain.trainer.schema import (
    CapturePayloadSchema,
    FightPayloadSchema,
    OnboardPayloadSchema,
)
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

    result = await onboarding(
        payload=payload, service=service, current_user=current_user
    )

    assert result is expected
    service.onboard.assert_awaited_once_with(current_user=current_user, payload=payload)


@pytest.mark.asyncio
async def test_capture_delegates_to_service(current_user: SimpleNamespace) -> None:
    payload = CapturePayloadSchema(pokemon_name="bulbasaur", nickname="Bulba")
    service = AsyncMock()
    expected = SimpleNamespace(id="trainer-id")
    service.capture.return_value = expected

    result = await capture(payload=payload, service=service, current_user=current_user)

    assert result is expected
    service.capture.assert_awaited_once_with(current_user=current_user, payload=payload)


@pytest.mark.asyncio
async def test_explore_delegates_to_service(current_user: SimpleNamespace) -> None:
    service = AsyncMock()
    expected = SimpleNamespace(id="event-id")
    service.explore.return_value = expected

    result = await explore(service=service, current_user=current_user)

    assert result is expected
    service.explore.assert_awaited_once_with(current_user=current_user)


@pytest.mark.asyncio
async def test_fight_delegates_to_service(current_user: SimpleNamespace) -> None:
    payload = FightPayloadSchema(
        battle_id="battle-id",
        owned_pokemon_move_id="move-id",
    )
    service = AsyncMock()
    expected = SimpleNamespace(id="battle-id")
    service.fight.return_value = expected

    result = await fight(payload=payload, service=service, current_user=current_user)

    assert result is expected
    service.fight.assert_awaited_once_with(current_user=current_user, payload=payload)
