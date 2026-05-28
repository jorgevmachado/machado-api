from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.shape.service import ShapeService


class TestShapeService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_returns_none_without_resource(
        shape_repository_mock: AsyncMock,
    ) -> None:
        service = ShapeService(repository=shape_repository_mock, client=AsyncMock())

        result = await service.sync_from_resource(None)

        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_returns_existing_entity(
        shape_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(name="quadruped")
        shape_repository_mock.find_by.return_value = existing
        service = ShapeService(repository=shape_repository_mock, client=AsyncMock())

        result = await service.sync_from_resource(
            {"name": "quadruped", "url": "https://pokeapi.co/api/v2/pokemon-shape/8/"}
        )

        assert result is existing

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_raises_when_name_is_missing(
        shape_repository_mock: AsyncMock,
    ) -> None:
        service = ShapeService(repository=shape_repository_mock, client=AsyncMock())

        with pytest.raises(ValueError, match="Name cannot be None"):
            await service.sync_from_resource(
                {"url": "https://pokeapi.co/api/v2/pokemon-shape/8/"}
            )

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_raises_when_url_is_missing(
        shape_repository_mock: AsyncMock,
    ) -> None:
        service = ShapeService(repository=shape_repository_mock, client=AsyncMock())

        with pytest.raises(ValueError, match="URL cannot be None"):
            await service.sync_from_resource({"name": "quadruped"})

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_saves_shape(
        shape_repository_mock: AsyncMock,
    ) -> None:
        saved = SimpleNamespace(name="quadruped")
        shape_repository_mock.save.return_value = saved
        service = ShapeService(repository=shape_repository_mock, client=AsyncMock())

        result = await service.sync_from_resource(
            {"name": "quadruped", "url": "https://pokeapi.co/api/v2/pokemon-shape/8/"}
        )

        assert result is saved
        saved_entity = shape_repository_mock.save.await_args.kwargs["entity"]
        assert saved_entity.name == "quadruped"
