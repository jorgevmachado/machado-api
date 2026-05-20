from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.route import get_trainer_home


@pytest.mark.asyncio
async def test_get_trainer_home_delegates_to_service():
    service = AsyncMock()
    expected = SimpleNamespace(trainer=SimpleNamespace(id="trainer-1"))
    service.get_home.return_value = expected
    current_user = SimpleNamespace(id="user-id")

    result = await get_trainer_home(current_user=current_user, service=service)

    assert result is expected
    service.get_home.assert_awaited_once_with(current_user)
