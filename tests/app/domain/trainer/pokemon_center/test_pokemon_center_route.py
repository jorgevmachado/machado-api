from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.pokemon_center.route import (
    get_healing_history_filter,
    get_pokemon_center_service,
    heal_pokemon_center_party,
    list_healing_history,
)


@pytest.mark.asyncio
async def test_route_factory_builds_service():
    service = get_pokemon_center_service(AsyncMock())

    assert service is not None


@pytest.mark.asyncio
async def test_route_handlers_delegate_to_service():
    trainer = SimpleNamespace(id='trainer-1')
    service = AsyncMock()
    service.heal_party.return_value = 'healed'
    service.list_history.return_value = ['history']

    assert await heal_pokemon_center_party(current_trainer=trainer, service=service) == 'healed'
    assert await list_healing_history(
        current_trainer=trainer,
        service=service,
        page_filter=SimpleNamespace(),
    ) == ['history']


def test_get_healing_history_filter_uses_defaults():
    page_filter = get_healing_history_filter()

    assert page_filter.limit == 12
    assert page_filter.clean_cache is False
