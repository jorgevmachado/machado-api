from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.domain.trainer.pokedex.repository import PokedexRepository
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

    def add_all(self, entities):
        self.added.extend(entities)

    async def flush(self):
        self.flushed = True


def build_base_pokemon(name="bulbasaur"):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        order=1,
        deleted_at=None,
        types=[],
    )


def build_repository(session=None):
    return PokedexRepository(session or FakeSession())


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_list_all_without_pagination_returns_all_items():
    session = FakeSession()
    session.scalars_result = [
        SimpleNamespace(pokemon=SimpleNamespace(name="bulbasaur"))
    ]
    repository = PokedexRepository(session)

    result = await repository.list_all(
        FilterPage.build(trainer_id=uuid4(), nickname="leaf")
    )

    assert len(result) == 1
    assert result[0].pokemon.name == "bulbasaur"



@pytest.mark.asyncio
async def test_find_by_returns_matching_entity():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(pokemon=SimpleNamespace(name="bulbasaur"))
    repository = PokedexRepository(session)

    result = await repository.find_by(trainer_id=uuid4(), pokemon_name="bulbasaur")

    assert result.pokemon.name == "bulbasaur"


@pytest.mark.asyncio
async def test_find_by_applies_id_pokemon_name_and_discovered_filters():
    session = FakeSession()
    session.scalar_result = SimpleNamespace(pokemon=SimpleNamespace(name='bulbasaur'))
    repository = PokedexRepository(session)

    result = await repository.find_by(
        trainer_id=uuid4(),
        id=uuid4(),
        pokemon_name='bulbasaur',
        discovered=True,
    )

    assert result.pokemon.name == 'bulbasaur'


@pytest.mark.asyncio
async def test_list_latest_discoveries_returns_loaded_entities():
    session = FakeSession()
    session.scalars_result = [SimpleNamespace(pokemon=SimpleNamespace(name="bulbasaur"))]
    repository = PokedexRepository(session)

    result = await repository.list_latest_discoveries(uuid4(), limit=3)

    assert len(result) == 1
    assert result[0].pokemon.name == "bulbasaur"
