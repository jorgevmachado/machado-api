from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.trainer.encounter import TrainerEncounterRepository
from app.models.enums import ExplorationEventTypeEnum
from app.shared.schemas import FilterPage


class FakeSession:
    def __init__(self):
        self.scalars_result = []
        self.scalar_result = None
        self.added = []
        self.flushed = False

    async def scalars(self, _query):
        return SimpleNamespace(all=lambda: self.scalars_result)

    async def scalar(self, _query):
        return self.scalar_result

    def add(self, entity):
        self.added.append(entity)

    def add_all(self, entities):
        self.added.extend(entities)

    async def flush(self):
        self.flushed = True


def build_repository(session=None):
    return TrainerEncounterRepository(session or FakeSession())


@pytest.mark.asyncio
async def test_list_encounters_for_pokemon_returns_all_loaded_entries():
    session = FakeSession()
    session.scalars_result = [SimpleNamespace(name="route-1")]
    repository = build_repository(session)

    result = await repository.list_encounters_for_pokemon("bulbasaur")

    assert [entry.name for entry in result] == ["route-1"]


@pytest.mark.asyncio
async def test_create_known_encounters_marks_only_the_active_entry():
    session = FakeSession()
    repository = build_repository(session)
    trainer_id = uuid4()
    active_id = uuid4()
    encounters = [SimpleNamespace(id=active_id), SimpleNamespace(id=uuid4())]

    result = await repository.create_known_encounters(
        trainer_id=trainer_id,
        encounters=encounters,
        active_encounter_id=active_id,
    )

    assert len(result) == 2
    assert session.flushed is True
    assert result[0].is_active is True
    assert result[1].is_active is False


@pytest.mark.asyncio
async def test_list_all_returns_loaded_entities():
    session = FakeSession()
    session.scalars_result = [SimpleNamespace(id=uuid4())]
    repository = build_repository(session)

    result = await repository.list_all(FilterPage.build(trainer_id=uuid4()))

    assert len(result) == 1


@pytest.mark.asyncio
async def test_find_by_returns_loaded_entity():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(id=uuid4())
    repository = build_repository(session)

    result = await repository.find_by(trainer_id=uuid4(), id=uuid4())

    assert result is session.scalar_result


@pytest.mark.asyncio
async def test_find_active_trainer_encounter_returns_loaded_entity():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(id=uuid4(), is_active=True)
    repository = build_repository(session)

    result = await repository.find_active_trainer_encounter(uuid4())

    assert result is session.scalar_result


@pytest.mark.asyncio
async def test_deactivate_all_encounters_clears_active_flags():
    session = FakeSession()
    session.scalars_result = [
        SimpleNamespace(is_active=True),
        SimpleNamespace(is_active=True),
    ]
    repository = build_repository(session)

    await repository.deactivate_all_encounters(uuid4())

    assert [entry.is_active for entry in session.scalars_result] == [False, False]
    assert session.flushed is True


@pytest.mark.asyncio
async def test_create_event_persists_payload_and_type():
    session = FakeSession()
    repository = build_repository(session)

    result = await repository.create_event(
        trainer_id=uuid4(),
        event_type=ExplorationEventTypeEnum.POKEBALLS,
        payload={"pokeballs_found": 2},
    )

    assert result.event_type == ExplorationEventTypeEnum.POKEBALLS
    assert result.payload == {"pokeballs_found": 2}
    assert session.flushed is True
