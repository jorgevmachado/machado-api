from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
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
        experience=5,
        special_attack=60,
        special_defense=50,
        nickname="char",
        pokemon_id=uuid4(),
        pokemon=SimpleNamespace(capture_rate=5),
        moves=[],
    )
    return SimpleNamespace(id=uuid4(), slot=1, is_active=True, owned_pokemon=owned)


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
        experience=56,
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
    assert saved.trainer_active_owned_pokemon_id == party.owned_pokemon.id
    assert saved.trainer_party_snapshot["name"] == party.owned_pokemon.name


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
    assert payload["wild_pokemon_name"] == wild_pokemon.name
    assert payload["exploration_event_id"] == str(exploration_event.id)
    assert payload["trainer_active_pokemon_id"] == str(party.owned_pokemon.id)


@pytest.mark.asyncio
async def test_get_raises_not_found_when_no_active_battle() -> None:
    trainer = SimpleNamespace(id=uuid4(), user=SimpleNamespace(id=uuid4()))
    service = BattleService(
        repository=_build_repository(AsyncMock()),
        trainer_log=AsyncMock(),
        pokedex_service=AsyncMock(),
        battle_log_service=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=None)

    with pytest.raises(Exception):
        await service.get(trainer=trainer)


@pytest.mark.asyncio
async def test_get_raises_when_battle_is_not_active() -> None:
    trainer = SimpleNamespace(id=uuid4(), user=SimpleNamespace(id=uuid4()))
    finished = SimpleNamespace(id=uuid4(), status=BattleSessionStatusEnum.ESCAPED)
    service = BattleService(
        repository=_build_repository(AsyncMock()),
        trainer_log=AsyncMock(),
        pokedex_service=AsyncMock(),
        battle_log_service=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=finished)

    with pytest.raises(Exception):
        await service.get(trainer=trainer)


@pytest.mark.asyncio
async def test_get_returns_active_battle_by_battle_id() -> None:
    trainer = SimpleNamespace(id=uuid4(), user=SimpleNamespace(id=uuid4()))
    active = SimpleNamespace(id=uuid4(), status=BattleSessionStatusEnum.ACTIVE)
    service = BattleService(
        repository=_build_repository(AsyncMock()),
        trainer_log=AsyncMock(),
        pokedex_service=AsyncMock(),
        battle_log_service=AsyncMock(),
    )
    service.find_one = AsyncMock(return_value=active)

    result = await service.get(trainer=trainer, battle_id=str(active.id))

    assert result is active
    service.find_one.assert_awaited_once_with(param=str(active.id), trainer_id=trainer.id)


@pytest.mark.asyncio
async def test_persist_increments_turn_and_creates_log_when_no_error() -> None:
    repository = _build_repository(AsyncMock())
    updated = SimpleNamespace(id=uuid4())
    repository.update = AsyncMock(return_value=updated)
    battle_log_service = AsyncMock()
    service = BattleService(
        repository=repository,
        trainer_log=AsyncMock(),
        pokedex_service=AsyncMock(),
        battle_log_service=battle_log_service,
    )
    battle_session = SimpleNamespace(
        id=uuid4(),
        status=BattleSessionStatusEnum.ACTIVE,
        turn_number=2,
        exploration_event_id=uuid4(),
    )
    trainer_party = SimpleNamespace(owned_pokemon=SimpleNamespace(id=uuid4()))
    battle_result = SimpleNamespace(error=False, status=BattleSessionStatusEnum.ACTIVE)

    with (
        patch(
            "app.domain.trainer.battle.service.build_payload",
            return_value={"message": "ok"},
        ),
        patch(
            "app.domain.trainer.battle.service.build_wild_pokemon_snapshot",
            return_value={"hp": 10},
        ),
        patch(
            "app.domain.trainer.battle.service.build_trainer_party_snapshot",
            return_value={"hp": 20},
        ),
        patch("app.domain.trainer.battle.service.utcnow", return_value="now"),
    ):
        result = await service.persist(
            wild_pokemon=SimpleNamespace(),
            trainer_party=trainer_party,
            battle_session=battle_session,
            battle_result=battle_result,
        )

    assert result is updated
    assert battle_session.turn_number == 3
    battle_log_service.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_keeps_turn_when_result_has_error() -> None:
    repository = _build_repository(AsyncMock())
    repository.update = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    service = BattleService(
        repository=repository,
        trainer_log=AsyncMock(),
        pokedex_service=AsyncMock(),
        battle_log_service=AsyncMock(),
    )
    battle_session = SimpleNamespace(
        id=uuid4(),
        status=BattleSessionStatusEnum.ACTIVE,
        turn_number=2,
        exploration_event_id=uuid4(),
    )
    trainer_party = SimpleNamespace(owned_pokemon=SimpleNamespace(id=uuid4()))
    battle_result = SimpleNamespace(error=True, status=BattleSessionStatusEnum.ACTIVE)

    with (
        patch(
            "app.domain.trainer.battle.service.build_payload",
            return_value={"message": "error"},
        ),
        patch(
            "app.domain.trainer.battle.service.build_wild_pokemon_snapshot",
            return_value={"hp": 10},
        ),
        patch(
            "app.domain.trainer.battle.service.build_trainer_party_snapshot",
            return_value={"hp": 20},
        ),
        patch("app.domain.trainer.battle.service.utcnow", return_value="now"),
    ):
        await service.persist(
            wild_pokemon=SimpleNamespace(),
            trainer_party=trainer_party,
            battle_session=battle_session,
            battle_result=battle_result,
        )

    assert battle_session.turn_number == 2
