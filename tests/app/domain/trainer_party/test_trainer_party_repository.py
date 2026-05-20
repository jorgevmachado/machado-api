from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.trainer.trainer_party import TrainerPartyRepository


class FakeSession:
    def __init__(self):
        self.scalars_result = []
        self.added = []
        self.flushed = False

    async def scalars(self, _query):
        return SimpleNamespace(all=lambda: self.scalars_result)

    def add_all(self, entities):
        self.added.extend(entities)

    async def flush(self):
        self.flushed = True


def build_repository(session=None):
    return TrainerPartyRepository(session or FakeSession())


@pytest.mark.asyncio
async def test_list_active_party_returns_loaded_entities():
    session = FakeSession()
    session.scalars_result = [SimpleNamespace(id=uuid4())]
    repository = build_repository(session)

    result = await repository.list_active_party(uuid4())

    assert len(result) == 1


@pytest.mark.asyncio
async def test_soft_delete_active_party_marks_rows_inactive():
    session = FakeSession()
    timestamp = datetime.now(timezone.utc)
    session.scalars_result = [
        SimpleNamespace(is_active=True, deleted_at=None),
        SimpleNamespace(is_active=True, deleted_at=None),
    ]
    repository = build_repository(session)

    await repository.soft_delete_active_party(uuid4(), timestamp)

    assert [entry.is_active for entry in session.scalars_result] == [False, False]
    assert [entry.deleted_at for entry in session.scalars_result] == [timestamp, timestamp]
    assert session.flushed is True


@pytest.mark.asyncio
async def test_list_owned_my_pokemon_returns_empty_without_ids():
    repository = build_repository()

    result = await repository.list_owned_my_pokemon(uuid4(), [])

    assert result == []


@pytest.mark.asyncio
async def test_list_owned_my_pokemon_returns_loaded_entities():
    session = FakeSession()
    session.scalars_result = [SimpleNamespace(id=uuid4())]
    repository = build_repository(session)

    result = await repository.list_owned_my_pokemon(uuid4(), [uuid4()])

    assert len(result) == 1


@pytest.mark.asyncio
async def test_create_party_creates_slots_in_order():
    session = FakeSession()
    repository = build_repository(session)
    trainer_id = uuid4()
    my_pokemons = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]

    result = await repository.create_party(
        trainer_id=trainer_id,
        my_pokemons=my_pokemons,
    )

    assert [entry.slot for entry in result] == [1, 2]
    assert session.flushed is True
