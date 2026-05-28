from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.habitat.service import HabitatService


class TestHabitatService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_returns_none_without_resource(
        habitat_repository_mock: AsyncMock,
    ) -> None:
        service = HabitatService(repository=habitat_repository_mock, client=AsyncMock())

        result = await service.sync_from_resource(None)

        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_returns_existing_entity(
        habitat_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(name="forest")
        habitat_repository_mock.find_by.return_value = existing
        service = HabitatService(repository=habitat_repository_mock, client=AsyncMock())

        result = await service.sync_from_resource(
            {"name": "forest", "url": "https://pokeapi.co/api/v2/pokemon-habitat/2/"}
        )

        assert result is existing

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_raises_when_name_is_missing(
        habitat_repository_mock: AsyncMock,
    ) -> None:
        service = HabitatService(repository=habitat_repository_mock, client=AsyncMock())

        with pytest.raises(ValueError, match="Name cannot be None"):
            await service.sync_from_resource(
                {"url": "https://pokeapi.co/api/v2/pokemon-habitat/2/"}
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_raises_when_url_is_missing(
        habitat_repository_mock: AsyncMock,
    ) -> None:
        service = HabitatService(repository=habitat_repository_mock, client=AsyncMock())

        with pytest.raises(ValueError, match="URL cannot be None"):
            await service.sync_from_resource({"name": "forest"})

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_saves_habitat(
        habitat_repository_mock: AsyncMock,
    ) -> None:
        saved = SimpleNamespace(name="forest")
        habitat_repository_mock.save.return_value = saved
        service = HabitatService(repository=habitat_repository_mock, client=AsyncMock())

        result = await service.sync_from_resource(
            {"name": "forest", "url": "https://pokeapi.co/api/v2/pokemon-habitat/2/"}
        )

        assert result is saved
        saved_entity = habitat_repository_mock.save.await_args.kwargs["entity"]
        assert saved_entity.name == "forest"
