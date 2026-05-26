from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.trainer.my_pokemon.service import MyPokemonService
from app.domain.trainer.pokemon_center.service import PokemonCenterService


def build_trainer():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        pokeballs=3,
        capture_rate=75,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
    )


def build_my_pokemon(*, hp: int, max_hp: int = 20, pp: int = 5, max_pp: int = 10):
    return SimpleNamespace(
        id=uuid4(),
        name='bulbasaur-owned',
        nickname='Leaf',
        hp=hp,
        max_hp=max_hp,
        updated_at=None,
        moves=[
            SimpleNamespace(
                id=uuid4(),
                pp=pp,
                max_pp=max_pp,
                deleted_at=None,
                updated_at=None,
            ),
        ],
    )


def build_party_entry(my_pokemon, slot: int = 1):
    return SimpleNamespace(
        id=uuid4(),
        slot=slot,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        deleted_at=None,
        my_pokemon=my_pokemon,
    )


def build_history_entry(*, trainer_id, my_pokemon, restored_hp: int, restored_pp: int, was_revived: bool):
    return {
        "id": uuid4(),
        "trainer_id": trainer_id,
        "pokemon_center_healing_id": uuid4(),
        "my_pokemon_id": my_pokemon.id,
        "action_type": "REVIVE_AND_HEAL" if was_revived else "FULL_HEAL",
        "payload": {
            "restored_hp": restored_hp,
            "restored_pp": restored_pp,
            "was_revived": was_revived,
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
        "deleted_at": None,
        "my_pokemon": my_pokemon,
    }


class FakeRepository:
    def __init__(self):
        self.session = AsyncMock()
        self.created_summary = None
        self.created_logs = None

    async def create_summary(self, entity):
        self.created_summary = entity
        return entity

    async def create_logs(self, entities):
        self.created_logs = entities
        return entities

    async def find_latest_by_trainer_id(self, _trainer_id):
        return self.created_summary

    async def list_history(self, *, trainer_id, page_filter=None):
        return []


class FakeTrainerPartyService:
    def __init__(self, party_entries):
        self.repository = SimpleNamespace(
            list_active_party=AsyncMock(return_value=party_entries),
        )


class FakeBattleSessionService:
    def __init__(self, has_active_battle: bool = False):
        self.has_active_battle = AsyncMock(return_value=has_active_battle)


def build_service(*, party_entries, has_active_battle: bool = False):
    repository = FakeRepository()
    service = PokemonCenterService(
        repository,
        trainer_party_service=FakeTrainerPartyService(party_entries),
        my_pokemon_service=SimpleNamespace(apply_full_healing=MyPokemonService.apply_full_healing),
        battle_session_service=FakeBattleSessionService(has_active_battle),
    )
    service.cache = SimpleNamespace(
        build_key=lambda *parts: ':'.join(str(part) for part in parts),
        delete_cache=AsyncMock(),
        delete_pattern=AsyncMock(),
    )
    service.history_cache_service.cache.delete_pattern = AsyncMock()
    return service, repository


@pytest.mark.asyncio
async def test_heal_party_restores_hp_pp_and_revives_active_party():
    trainer = build_trainer()
    my_pokemon = build_my_pokemon(hp=0, pp=4, max_pp=10)
    service, repository = build_service(
        party_entries=[build_party_entry(my_pokemon)],
    )

    result = await service.heal_party(trainer)

    assert result.success is True
    assert result.healing_summary is not None
    assert result.healing_summary.healed_pokemon_quantity == 1
    assert result.healing_summary.restored_hp == 20
    assert result.healing_summary.restored_pp == 6
    assert result.restored_pokemon[0].was_revived is True
    assert my_pokemon.hp == my_pokemon.max_hp
    assert my_pokemon.moves[0].pp == my_pokemon.moves[0].max_pp
    repository.session.commit.assert_awaited_once()
    service.cache.delete_cache.assert_awaited()
    service.cache.delete_pattern.assert_awaited()


@pytest.mark.asyncio
async def test_heal_party_returns_success_without_persisting_when_party_is_already_fully_healed():
    trainer = build_trainer()
    my_pokemon = build_my_pokemon(hp=20, pp=10, max_pp=10)
    service, repository = build_service(
        party_entries=[build_party_entry(my_pokemon)],
    )

    result = await service.heal_party(trainer)

    assert result.success is True
    assert result.healing_summary is None
    assert result.restored_pokemon == []
    repository.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_heal_party_blocks_when_battle_is_active():
    trainer = build_trainer()
    service, repository = build_service(
        party_entries=[build_party_entry(build_my_pokemon(hp=0))],
        has_active_battle=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.heal_party(trainer)

    assert exc_info.value.status_code == 409
    repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_heal_party_requires_active_party():
    trainer = build_trainer()
    service, repository = build_service(
        party_entries=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.heal_party(trainer)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Trainer has no active party"
    repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_history_returns_itemized_entries():
    trainer = build_trainer()
    my_pokemon = build_my_pokemon(hp=20, pp=10, max_pp=10)
    service, repository = build_service(
        party_entries=[build_party_entry(my_pokemon)],
    )
    service.history_cache_service.get_list = AsyncMock(return_value=None)
    service.history_cache_service.set_list = AsyncMock()
    repository.list_history = AsyncMock(return_value=[build_history_entry(
        trainer_id=trainer.id,
        my_pokemon=my_pokemon,
        restored_hp=8,
        restored_pp=4,
        was_revived=False,
    )])

    result = await service.list_history(trainer)

    assert len(result) == 1
    assert result[0].restored_hp == 8
    assert result[0].restored_pp == 4
    assert result[0].was_revived is False
    repository.list_history.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_latest_summary_returns_none_when_no_history():
    trainer = build_trainer()
    service, repository = build_service(
        party_entries=[build_party_entry(build_my_pokemon(hp=20))],
    )
    repository.find_latest_by_trainer_id = AsyncMock(return_value=None)

    result = await service.get_latest_summary(trainer.id)

    assert result is None


@pytest.mark.asyncio
async def test_get_latest_summary_serializes_entity():
    trainer = build_trainer()
    service, repository = build_service(
        party_entries=[build_party_entry(build_my_pokemon(hp=20))],
    )
    summary = SimpleNamespace(
        id=uuid4(),
        healed_pokemon_quantity=1,
        restored_hp=5,
        restored_pp=3,
        created_at=datetime.now(timezone.utc),
    )
    repository.find_latest_by_trainer_id = AsyncMock(return_value=summary)

    result = await service.get_latest_summary(trainer.id)

    assert result is not None
    assert result.id == summary.id
    assert result.restored_hp == 5
    assert result.restored_pp == 3


@pytest.mark.asyncio
async def test_list_history_returns_cached_value_when_available():
    trainer = build_trainer()
    service, repository = build_service(
        party_entries=[build_party_entry(build_my_pokemon(hp=20))],
    )
    cached = ["cached-history"]
    service.history_cache_service.get_list = AsyncMock(return_value=cached)
    repository.list_history = AsyncMock()

    result = await service.list_history(trainer)

    assert result == cached
    repository.list_history.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_history_serializes_paginated_payload():
    trainer = build_trainer()
    my_pokemon = build_my_pokemon(hp=20, pp=10, max_pp=10)
    service, repository = build_service(
        party_entries=[build_party_entry(my_pokemon)],
    )
    service.history_cache_service.get_list = AsyncMock(return_value=None)
    service.history_cache_service.set_list = AsyncMock()

    class FakePaginatedHistory:
        def __init__(self, items):
            self.items = items

        def model_copy(self, update):
            return {
                "items": update["items"],
                "kind": "paginated",
            }

    repository.list_history = AsyncMock(
        return_value=FakePaginatedHistory(
            [
                build_history_entry(
                    trainer_id=trainer.id,
                    my_pokemon=my_pokemon,
                    restored_hp=2,
                    restored_pp=1,
                    was_revived=False,
                )
            ]
        )
    )

    result = await service.list_history(trainer)

    assert result["kind"] == "paginated"
    assert len(result["items"]) == 1
    assert result["items"][0].restored_hp == 2
    assert result["items"][0].restored_pp == 1
