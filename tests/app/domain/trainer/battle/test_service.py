from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.trainer.battle.service import BattleService
from app.models.enums import BattleSessionStatusEnum


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.save = AsyncMock()
    repository.find_by = AsyncMock(return_value=None)
    return repository


def _build_party():
    owned = SimpleNamespace(
        id=uuid4(),
        name="charmander",
        hp=49,
        max_hp=49,
        attack=52,
        defense=43,
        speed=65,
        level=5,
        special_attack=60,
        special_defense=50,
        nickname="char",
        moves=[],
    )
    return SimpleNamespace(slot=1, is_active=True, owned_pokemon=owned)


def _build_trainer():
    return SimpleNamespace(id=uuid4())


def _build_exploration_event(pokemon_name: str = "pidgey"):
    return SimpleNamespace(
        id=uuid4(),
        payload={"wild_pokemon_name": pokemon_name},
    )


def _build_wild_pokemon():
    return SimpleNamespace(
        id=uuid4(),
        name="pidgey",
        level=5,
        pokemon_id=uuid4(),
        hp=40,
        max_hp=40,
        attack=45,
        defense=40,
        speed=56,
        special_attack=35,
        special_defense=35,
        pokemon=SimpleNamespace(
            id=uuid4(),
            name="pidgey",
            capture_rate=255,
            moves=[],
        ),
    )


def test_from_session_builds_service():
    service = BattleService.from_session(AsyncMock())
    assert isinstance(service, BattleService)


@pytest.mark.asyncio
async def test_create_or_resume_returns_existing_active_session():
    session = AsyncMock()
    repository = _build_repository(session)
    existing = SimpleNamespace(id=uuid4(), status=BattleSessionStatusEnum.ACTIVE)
    service = BattleService(
        repository=repository,
        trainer_log=AsyncMock(),
        pokedex_service=AsyncMock(),
        battle_log_service=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=existing)

    result = await service.create_or_resume(
        party=_build_party(),
        trainer=_build_trainer(),
        exploration_event=_build_exploration_event(),
    )

    assert result is existing
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_or_resume_creates_new_session_when_none_active():
    session = AsyncMock()
    repository = _build_repository(session)
    wild_pokemon = _build_wild_pokemon()
    party = _build_party()
    trainer = _build_trainer()
    exploration_event = _build_exploration_event(pokemon_name=wild_pokemon.name)

    saved_entity = SimpleNamespace(
        id=uuid4(),
        status=BattleSessionStatusEnum.ACTIVE,
    )
    repository.save.return_value = saved_entity

    pokedex_service = AsyncMock()
    pokedex_service.find_one_cached = AsyncMock(return_value=wild_pokemon)
    battle_log_service = AsyncMock()
    battle_log_service.start = AsyncMock()

    service = BattleService(
        repository=repository,
        trainer_log=AsyncMock(),
        pokedex_service=pokedex_service,
        battle_log_service=battle_log_service,
    )
    service.find_by = AsyncMock(return_value=None)

    result = await service.create_or_resume(
        party=party,
        trainer=trainer,
        exploration_event=exploration_event,
    )

    assert result is saved_entity
    repository.save.assert_awaited_once()
    battle_log_service.start.assert_awaited_once()

    saved = repository.save.await_args.kwargs["entity"]
    assert saved.trainer_id == trainer.id
    assert saved.wild_pokemon_id == wild_pokemon.id
    assert saved.wild_pokemon_name == wild_pokemon.name
    assert saved.trainer_active_owned_pokemon_id == party.owned_pokemon.id
    assert isinstance(saved.trainer_party_snapshot, list)


@pytest.mark.asyncio
async def test_create_or_resume_passes_correct_payload_to_battle_log():
    session = AsyncMock()
    repository = _build_repository(session)
    wild_pokemon = _build_wild_pokemon()
    party = _build_party()
    trainer = _build_trainer()
    exploration_event = _build_exploration_event(pokemon_name=wild_pokemon.name)

    saved_entity = SimpleNamespace(id=uuid4(), status=BattleSessionStatusEnum.ACTIVE)
    repository.save.return_value = saved_entity

    pokedex_service = AsyncMock()
    pokedex_service.find_one_cached = AsyncMock(return_value=wild_pokemon)
    battle_log_service = AsyncMock()
    battle_log_service.start = AsyncMock()

    service = BattleService(
        repository=repository,
        trainer_log=AsyncMock(),
        pokedex_service=pokedex_service,
        battle_log_service=battle_log_service,
    )
    service.find_by = AsyncMock(return_value=None)

    await service.create_or_resume(
        party=party,
        trainer=trainer,
        exploration_event=exploration_event,
    )

    call_kwargs = battle_log_service.start.await_args.kwargs
    assert call_kwargs["battle_session_id"] == saved_entity.id
    payload = call_kwargs["payload"]
    assert payload["pokemon_name"] == wild_pokemon.name
    assert payload["exploration_event_id"] == str(exploration_event.id)
    assert payload["trainer_active_owned_pokemon_id"] == str(party.owned_pokemon.id)
