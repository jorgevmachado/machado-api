from unittest.mock import AsyncMock

from sqlalchemy import select

from app.domain.pokemon.repository import PokemonRepository
from app.models import Pokemon
from app.models.enums import PokemonStatusEnum
from app.shared.schemas import FilterPage


def test_apply_filters_adds_list_predicates():
    repository = PokemonRepository(session=AsyncMock())
    page_filter = FilterPage.build(
        name="saur",
        order=1,
        status=PokemonStatusEnum.INCOMPLETE,
        type="grass",
    )

    query = repository._apply_filters(select(Pokemon), page_filter)
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

    assert "pokemons.deleted_at IS NULL" in compiled
    assert "lower(pokemons.name) LIKE lower" in compiled
    assert 'pokemons."order" = 1' in compiled
    assert "EXISTS" in compiled
    assert "pokemon_types.name = " in compiled
