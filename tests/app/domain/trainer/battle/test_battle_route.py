from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.trainer.battle.route import (
    capture_battle_pokemon,
    flee_battle,
    get_active_battle,
    get_battle_session_service,
    get_trainer_service,
    list_battle_logs,
    switch_battle_pokemon,
    use_battle_move,
)
from app.domain.trainer.battle.schema import (
    CaptureBattlePokemonSchema,
    SwitchBattlePokemonSchema,
    UseBattleMoveSchema,
)


@pytest.mark.asyncio
async def test_route_factory_builds_service():
    service = get_battle_session_service(AsyncMock())
    trainer_service = get_trainer_service(AsyncMock())

    assert service is not None
    assert trainer_service is not None


@pytest.mark.asyncio
async def test_route_handlers_delegate_to_service():
    trainer = SimpleNamespace(id='trainer-1')
    service = AsyncMock()
    service.get_active_battle.return_value = 'active'
    service.use_move.return_value = 'move'
    service.switch_pokemon.return_value = 'switch'
    service.flee.return_value = 'flee'
    service.list_logs.return_value = ['log']
    trainer_service = AsyncMock()
    trainer_service.capture_battle_pokemon.return_value = 'capture'

    assert await get_active_battle(current_trainer=trainer, service=service) == 'active'
    assert await use_battle_move(
        payload=UseBattleMoveSchema(move_id='00000000-0000-0000-0000-000000000001'),
        current_trainer=trainer,
        service=service,
    ) == 'move'
    assert await switch_battle_pokemon(
        payload=SwitchBattlePokemonSchema(my_pokemon_id='00000000-0000-0000-0000-000000000001'),
        current_trainer=trainer,
        service=service,
    ) == 'switch'
    assert await flee_battle(current_trainer=trainer, service=service) == 'flee'
    assert await capture_battle_pokemon(
        payload=CaptureBattlePokemonSchema(nickname='Sparky'),
        current_trainer=trainer,
        service=trainer_service,
    ) == 'capture'
    assert await list_battle_logs(current_trainer=trainer, service=service) == ['log']
