from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.growth_rate.service import GrowthRateService


class TestGrowthRateService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_returns_none_without_resource(
        growth_rate_repository_mock: AsyncMock,
    ) -> None:
        service = GrowthRateService(
            repository=growth_rate_repository_mock, client=AsyncMock()
        )

        result = await service.sync_from_resource(None)

        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_resource_delegates_to_get_or_create(
        growth_rate_repository_mock: AsyncMock,
    ) -> None:
        service = GrowthRateService(
            repository=growth_rate_repository_mock, client=AsyncMock()
        )
        expected = SimpleNamespace(name="medium")
        service.get_or_create = AsyncMock(return_value=expected)

        result = await service.sync_from_resource(
            {"url": "https://pokeapi.co/api/v2/growth-rate/2/"}
        )

        assert result is expected
        service.get_or_create.assert_awaited_once_with(
            order=2, url="https://pokeapi.co/api/v2/growth-rate/2/"
        )

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_entity(
        growth_rate_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(name="medium")
        growth_rate_repository_mock.find_by.return_value = existing
        service = GrowthRateService(
            repository=growth_rate_repository_mock, client=AsyncMock()
        )

        result = await service.get_or_create(order=2, url="url")

        assert result is existing

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_raises_when_external_is_missing(
        growth_rate_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_growth_rate.return_value = None
        service = GrowthRateService(
            repository=growth_rate_repository_mock, client=client
        )

        with pytest.raises(ValueError, match="External growth rate not found"):
            await service.get_or_create(order=2, url="url")

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_or_create_saves_external_growth_rate(
        growth_rate_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_growth_rate.return_value = SimpleNamespace(
            name="medium",
            formula="x^3",
            descriptions=[
                {"language": {"name": "en"}, "description": "Balanced growth"}
            ],
        )
        saved = SimpleNamespace(name="medium")
        growth_rate_repository_mock.save.return_value = saved
        service = GrowthRateService(
            repository=growth_rate_repository_mock, client=client
        )

        result = await service.get_or_create(
            order=2, url="https://pokeapi.co/api/v2/growth-rate/2/"
        )

        assert result is saved
        saved_entity = growth_rate_repository_mock.save.await_args.kwargs["entity"]
        assert saved_entity.formula == "x^3"
        assert saved_entity.description == "Balanced growth"
