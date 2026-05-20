from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.trainer.my_pokemon import MyPokemonRepository
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

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_list_all_without_pagination_returns_all_items():
    session = FakeSession()
    session.scalars_result = [SimpleNamespace(name="bulbasaur")]
    repository = MyPokemonRepository(session)

    result = await repository.list_all(FilterPage.build(trainer_id=uuid4()))

    assert [item.name for item in result] == ["bulbasaur"]


@pytest.mark.asyncio
async def test_find_by_returns_scoped_entity():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(name="bulbasaur")
    repository = MyPokemonRepository(session)

    result = await repository.find_by(trainer_id=uuid4(), name="bulbasaur")

    assert result.name == "bulbasaur"


@pytest.mark.asyncio
async def test_find_by_applies_id_and_pokemon_name_filters():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(name="bulbasaur")
    repository = MyPokemonRepository(session)

    result = await repository.find_by(
        trainer_id=uuid4(),
        id=uuid4(),
        pokemon_name='bulbasaur',
    )

    assert result.name == 'bulbasaur'


@pytest.mark.asyncio
async def test_find_base_pokemon_returns_base_catalog_entry():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(name="bulbasaur")
    repository = MyPokemonRepository(session)

    result = await repository.find_base_pokemon("bulbasaur")

    assert result.name == "bulbasaur"
