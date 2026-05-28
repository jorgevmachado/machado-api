from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.repository import PokemonRepository
from app.domain.pokemon.service import PokemonService
from tests.conftest import FakeSession


@pytest.fixture
def pokemon_page() -> SimpleNamespace:
    return SimpleNamespace(items=[])


@pytest.fixture
def pokemon_repository_mock(pokemon_page: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        session=SimpleNamespace(),
        list_all=AsyncMock(return_value=pokemon_page),
    )


@pytest.fixture
def pokemon_service_factory():
    def _factory(repository, client=None) -> PokemonService:
        empty_collection_service = SimpleNamespace(
            sync_from_resources=AsyncMock(return_value=[])
        )
        return PokemonService(
            repository,
            client=client or AsyncMock(),
            type_service=empty_collection_service,
            ability_service=SimpleNamespace(
                sync_from_resources=AsyncMock(return_value=[])
            ),
            move_service=empty_collection_service,
            image_service=SimpleNamespace(sync_from_sprites=AsyncMock()),
            growth_rate_service=SimpleNamespace(
                sync_from_resource=AsyncMock(return_value=None)
            ),
            habitat_service=SimpleNamespace(
                sync_from_resource=AsyncMock(return_value=None)
            ),
            shape_service=SimpleNamespace(
                sync_from_resource=AsyncMock(return_value=None)
            ),
            encounter_service=SimpleNamespace(
                sync_from_resources=AsyncMock(return_value=[])
            ),
        )

    return _factory


@pytest.fixture
def pokemon_service(
    pokemon_repository_mock: SimpleNamespace,
    pokemon_service_factory,
) -> PokemonService:
    service = pokemon_service_factory(pokemon_repository_mock)
    service._ensure_initial_catalog = AsyncMock()
    return service


@pytest.fixture
def pokemon_fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def pokemon_repository(pokemon_fake_session: FakeSession) -> PokemonRepository:
    return PokemonRepository(session=cast(Any, pokemon_fake_session))


@pytest.fixture
def current_user() -> SimpleNamespace:
    return SimpleNamespace(id="user-id", username="username")


@pytest.fixture
def pokemon_route_service() -> AsyncMock:
    return AsyncMock()
