from types import SimpleNamespace

import pytest

from app.domain.pokemon.repository import PokemonRepository
from tests.conftest import FakeSession


class TestPokemonRepository:
    @staticmethod
    @pytest.mark.asyncio
    async def test_list_by_names_returns_empty_list_when_no_names(
        pokemon_repository: PokemonRepository,
    ) -> None:
        result = await pokemon_repository.list_by_names(names=set())

        assert result == []

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_by_names_returns_pokemons_from_scalar_result(
        pokemon_repository: PokemonRepository,
        pokemon_fake_session: FakeSession,
    ) -> None:
        pokemon_fake_session.scalars_result = [
            SimpleNamespace(name="bulbasaur"),
            SimpleNamespace(name="charmander"),
            SimpleNamespace(name="squirtle"),
        ]

        result = await pokemon_repository.list_by_names(
            names={"bulbasaur", "charmander", "squirtle"}
        )

        assert len(result) == 3
