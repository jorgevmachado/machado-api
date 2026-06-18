from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.party.business import MAX_PARTY_SIZE
from app.domain.trainer.party.service import TrainerPartyService
from app.domain.trainer.progression import AttributesCalculatedSchema


def _build_repository(session: AsyncMock) -> AsyncMock:
    repository = AsyncMock()
    repository.session = session
    repository.list_all = AsyncMock()
    repository.find_by = AsyncMock()
    repository.save = AsyncMock()
    return repository


def _build_trainer(party_slots=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        party_slots=party_slots,
        user=SimpleNamespace(id=uuid4()),
    )


def test_from_session_builds_service() -> None:
    service = TrainerPartyService.from_session(AsyncMock())
    assert isinstance(service, TrainerPartyService)


@pytest.mark.asyncio
async def test_add_returns_existing_list_when_owned_pokemon_already_in_party(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    party_list = [SimpleNamespace(id=uuid4())]
    repository.list_all.return_value = party_list
    repository.find_by.return_value = SimpleNamespace(id=uuid4())
    service = TrainerPartyService(repository=repository, trainer_log=AsyncMock())

    result = await service.add(
        trainer=trainer,
        owned_pokemon=SimpleNamespace(id=uuid4()),
    )

    assert result is party_list
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_uses_paginated_items_and_saves_new_slot(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    repository.list_all.side_effect = [
        SimpleNamespace(items=[SimpleNamespace(id=uuid4())]),
        ["updated"],
    ]
    repository.find_by.return_value = None
    service = TrainerPartyService(repository=repository, trainer_log=AsyncMock())
    owned_pokemon = SimpleNamespace(id=uuid4())

    result = await service.add(
        trainer=trainer,
        owned_pokemon=owned_pokemon,
        is_active=False,
    )

    assert result == ["updated"]
    repository.save.assert_awaited_once()
    saved_entity = repository.save.await_args.kwargs["entity"]
    assert saved_entity.slot == 2
    assert saved_entity.is_active is False
    assert saved_entity.owned_pokemon_id == owned_pokemon.id


@pytest.mark.asyncio
async def test_add_returns_existing_party_when_full_and_without_throw(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    full_party = [SimpleNamespace(id=uuid4()) for _ in range(MAX_PARTY_SIZE)]
    repository.list_all.return_value = full_party
    repository.find_by.return_value = None
    service = TrainerPartyService(repository=repository, trainer_log=AsyncMock())

    result = await service.add(
        trainer=trainer,
        owned_pokemon=SimpleNamespace(id=uuid4()),
        without_throw=True,
    )

    assert result is full_party
    repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_raises_when_party_is_full_and_without_throw_is_false(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    repository = _build_repository(trainer_session)
    repository.list_all.return_value = [
        SimpleNamespace(id=uuid4()) for _ in range(MAX_PARTY_SIZE)
    ]
    repository.find_by.return_value = None
    service = TrainerPartyService(repository=repository, trainer_log=AsyncMock())

    with pytest.raises(HTTPException, match="already have"):
        await service.add(
            trainer=trainer,
            owned_pokemon=SimpleNamespace(id=uuid4()),
            without_throw=False,
        )


@pytest.mark.asyncio
async def test_get_or_create_list_returns_given_party_slots(
    trainer_session: AsyncMock,
) -> None:
    party_slots = [SimpleNamespace(id=uuid4())]
    trainer = _build_trainer(party_slots=party_slots)
    service = TrainerPartyService(
        repository=_build_repository(trainer_session), trainer_log=AsyncMock()
    )

    result = await service.get_or_create_list(
        trainer=trainer,
        owned_pokemon=SimpleNamespace(id=uuid4()),
    )

    assert result is party_slots


@pytest.mark.asyncio
async def test_get_or_create_list_returns_existing_party_slots_from_list_all(
    trainer_session: AsyncMock,
) -> None:
    existing = [SimpleNamespace(id=uuid4())]
    trainer = _build_trainer(party_slots=None)
    service = TrainerPartyService(
        repository=_build_repository(trainer_session), trainer_log=AsyncMock()
    )
    service.list_all = AsyncMock(return_value=existing)

    result = await service.get_or_create_list(
        trainer=trainer,
        owned_pokemon=SimpleNamespace(id=uuid4()),
    )

    assert result is existing


@pytest.mark.asyncio
async def test_get_or_create_list_returns_empty_when_owned_pokemon_is_missing(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer(party_slots=None)
    service = TrainerPartyService(
        repository=_build_repository(trainer_session), trainer_log=AsyncMock()
    )
    service.list_all = AsyncMock(return_value=[])
    service.add = AsyncMock()

    result = await service.get_or_create_list(
        trainer=trainer,
        owned_pokemon=None,
    )

    assert result == []
    service.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_list_delegates_to_add_when_needed(
    trainer_session: AsyncMock,
) -> None:
    expected = [SimpleNamespace(id=uuid4())]
    owned_pokemon = SimpleNamespace(id=uuid4())
    trainer = _build_trainer(party_slots=[])
    service = TrainerPartyService(
        repository=_build_repository(trainer_session), trainer_log=AsyncMock()
    )
    service.list_all = AsyncMock(return_value=[])
    service.add = AsyncMock(return_value=expected)

    result = await service.get_or_create_list(
        trainer=trainer,
        owned_pokemon=owned_pokemon,
    )

    assert result is expected
    service.add.assert_awaited_once_with(
        trainer=trainer,
        owned_pokemon=owned_pokemon,
        without_throw=True,
    )


# ── ready_to_battle ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ready_to_battle_raises_when_no_parties(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    trainer.user = SimpleNamespace(id=uuid4())
    service = TrainerPartyService(
        repository=_build_repository(trainer_session), trainer_log=AsyncMock()
    )
    service.list_all = AsyncMock(return_value=[])

    with pytest.raises(HTTPException) as exc_info:
        await service.ready_to_battle(trainer=trainer)

    assert exc_info.value.status_code == 400
    assert "no active party" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ready_to_battle_returns_first_pokemon_with_hp(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    fainted = SimpleNamespace(owned_pokemon=SimpleNamespace(hp=0))
    alive = SimpleNamespace(owned_pokemon=SimpleNamespace(hp=35))
    service = TrainerPartyService(
        repository=_build_repository(trainer_session), trainer_log=AsyncMock()
    )
    service.list_all = AsyncMock(return_value=[fainted, alive])

    result = await service.ready_to_battle(trainer=trainer)

    assert result is alive


@pytest.mark.asyncio
async def test_ready_to_battle_raises_when_all_pokemon_fainted(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    trainer.user = SimpleNamespace(id=uuid4())
    fainted1 = SimpleNamespace(owned_pokemon=SimpleNamespace(hp=0))
    fainted2 = SimpleNamespace(owned_pokemon=SimpleNamespace(hp=0))
    service = TrainerPartyService(
        repository=_build_repository(trainer_session), trainer_log=AsyncMock()
    )
    service.list_all = AsyncMock(return_value=[fainted1, fainted2])

    with pytest.raises(HTTPException) as exc_info:
        await service.ready_to_battle(trainer=trainer)

    assert exc_info.value.status_code == 400
    assert "battle-ready" in exc_info.value.detail


@pytest.mark.asyncio
async def test_preparation_for_battle_raises_when_active_party_not_found(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    service = TrainerPartyService(
        repository=_build_repository(trainer_session),
        trainer_log=AsyncMock(),
        owned_pokemon_service=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=None)

    with pytest.raises(HTTPException, match="No active party slot"):
        await service.preparation_for_battle(
            trainer=trainer,
            owned_pokemon_id=uuid4(),
            owned_pokemon_move_id="move-id",
        )


@pytest.mark.asyncio
async def test_preparation_for_battle_raises_when_owned_pokemon_is_fainted(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    trainer_party = SimpleNamespace(owned_pokemon=SimpleNamespace(hp=0, name="pikachu"))
    service = TrainerPartyService(
        repository=_build_repository(trainer_session),
        trainer_log=AsyncMock(),
        owned_pokemon_service=AsyncMock(),
    )
    service.find_by = AsyncMock(return_value=trainer_party)

    with pytest.raises(HTTPException, match="already fainted"):
        await service.preparation_for_battle(
            trainer=trainer,
            owned_pokemon_id=uuid4(),
            owned_pokemon_move_id="move-id",
        )


@pytest.mark.asyncio
async def test_preparation_for_battle_raises_when_selected_move_is_missing(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    trainer_party = SimpleNamespace(owned_pokemon=SimpleNamespace(hp=10, name="pikachu"))
    owned_service = AsyncMock()
    owned_service.select_move_to_battle = AsyncMock(return_value=None)
    service = TrainerPartyService(
        repository=_build_repository(trainer_session),
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_service,
    )
    service.find_by = AsyncMock(return_value=trainer_party)

    with pytest.raises(HTTPException, match="not found for owned Pokemon"):
        await service.preparation_for_battle(
            trainer=trainer,
            owned_pokemon_id=uuid4(),
            owned_pokemon_move_id="missing-move",
        )


@pytest.mark.asyncio
async def test_preparation_for_battle_returns_schema_when_valid(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    owned_pokemon_id = uuid4()
    trainer_party = SimpleNamespace(owned_pokemon=SimpleNamespace(hp=10, name="pikachu"))
    selected_move = SimpleNamespace(id=uuid4())
    owned_service = AsyncMock()
    owned_service.select_move_to_battle = AsyncMock(return_value=selected_move)
    service = TrainerPartyService(
        repository=_build_repository(trainer_session),
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_service,
    )
    service.find_by = AsyncMock(return_value=trainer_party)

    expected = SimpleNamespace(
        trainer_party=trainer_party,
        trainer_party_selected_move=selected_move,
    )
    with patch(
        "app.domain.trainer.party.service.TrainerPartyBattleSchema",
        return_value=expected,
    ):
        result = await service.preparation_for_battle(
            trainer=trainer,
            owned_pokemon_id=owned_pokemon_id,
            owned_pokemon_move_id="move-id",
        )

    assert result is expected


@pytest.mark.asyncio
async def test_update_after_battle_returns_same_party_when_no_changes(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    trainer.user.username = "ash"
    owned = SimpleNamespace(
        hp=30,
        level=5,
        speed=10,
        attack=10,
        max_hp=35,
        defense=10,
        experience=100,
        special_attack=10,
        special_defense=10,
    )
    trainer_party = SimpleNamespace(id=uuid4(), owned_pokemon=owned)
    progression = AttributesCalculatedSchema(
        hp=30,
        level=5,
        speed=10,
        attack=10,
        max_hp=35,
        defense=10,
        level_up=False,
        experience=100,
        special_attack=10,
        special_defense=10,
    )
    owned_service = AsyncMock()
    service = TrainerPartyService(
        repository=_build_repository(trainer_session),
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_service,
    )
    service.find_one = AsyncMock()

    result = await service.update_after_battle(
        trainer=trainer,
        trainer_party=trainer_party,
        selected_pokemon_progression=progression,
    )

    assert result is trainer_party
    owned_service.update_entity.assert_not_awaited()
    service.find_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_after_battle_updates_and_reloads_party(
    trainer_session: AsyncMock,
) -> None:
    trainer = _build_trainer()
    trainer.user.username = "ash"
    owned = SimpleNamespace(
        hp=30,
        level=5,
        speed=10,
        attack=10,
        max_hp=35,
        defense=10,
        experience=100,
        special_attack=10,
        special_defense=10,
    )
    trainer_party = SimpleNamespace(id=uuid4(), owned_pokemon=owned)
    progression = AttributesCalculatedSchema(
        hp=50,
        level=6,
        speed=20,
        attack=21,
        max_hp=55,
        defense=22,
        level_up=True,
        experience=200,
        special_attack=23,
        special_defense=24,
    )
    owned_service = AsyncMock()
    service = TrainerPartyService(
        repository=_build_repository(trainer_session),
        trainer_log=AsyncMock(),
        owned_pokemon_service=owned_service,
    )
    reloaded = SimpleNamespace(id=trainer_party.id)
    service.find_one = AsyncMock(return_value=reloaded)

    result = await service.update_after_battle(
        trainer=trainer,
        trainer_party=trainer_party,
        selected_pokemon_progression=progression,
    )

    assert result is reloaded
    assert owned.hp == 50
    assert owned.level == 6
    assert owned.speed == 20
    owned_service.update_entity.assert_awaited_once_with(entity=owned)
