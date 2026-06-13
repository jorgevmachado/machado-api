from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.party.business import MAX_PARTY_SIZE
from app.domain.trainer.party.service import TrainerPartyService


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
