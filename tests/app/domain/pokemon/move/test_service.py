from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.domain.pokemon.move.service import MoveService


class TestMoveService:
    @pytest.mark.asyncio
    async def test_sync_from_resources_collects_created_moves(
        self,
        move_repository_mock: AsyncMock,
    ) -> None:
        service = MoveService(repository=move_repository_mock, client=AsyncMock())
        service.get_or_create = AsyncMock(
            side_effect=[SimpleNamespace(name="tackle"), None]
        )

        result = await service.sync_from_resources(
            resources=[{"move": {"url": "https://pokeapi.co/api/v2/move/33/"}}, {}]
        )

        assert len(result) == 1
        assert result[0].name == "tackle"

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_entity(
        self,
        move_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(name="tackle")
        move_repository_mock.find_by.return_value = existing
        service = MoveService(repository=move_repository_mock, client=AsyncMock())

        result = await service.get_or_create(
            resource={"url": "https://pokeapi.co/api/v2/move/33/"}
        )

        assert result is existing

    @pytest.mark.asyncio
    async def test_get_or_create_returns_none_on_timeout(
        self,
        move_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_move.side_effect = httpx.TimeoutException("timeout")
        service = MoveService(repository=move_repository_mock, client=client)

        result = await service.get_or_create(
            resource={"url": "https://pokeapi.co/api/v2/move/33/"}
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_raises_when_external_resource_is_missing(
        self,
        move_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_move.return_value = None
        service = MoveService(repository=move_repository_mock, client=client)

        with pytest.raises(ValueError, match="External move not found"):
            await service.get_or_create(
                resource={"url": "https://pokeapi.co/api/v2/move/33/"}
            )

    @pytest.mark.asyncio
    async def test_get_or_create_saves_external_move(
        self,
        move_repository_mock: AsyncMock,
    ) -> None:
        client = AsyncMock()
        client.get_move.return_value = SimpleNamespace(
            pp=35,
            name="tackle",
            type=SimpleNamespace(name="normal"),
            power=None,
            target=SimpleNamespace(name="selected-pokemon"),
            effect_entries=[
                {
                    "language": {"name": "en"},
                    "effect": "Deals damage.",
                    "short_effect": "Deals damage",
                }
            ],
            priority=0,
            accuracy=None,
            flavor_text_entries=[
                {
                    "language": {"name": "en"},
                    "version_group": {"name": "gold-silver"},
                    "flavor_text": "A physical attack.",
                }
            ],
            damage_class=SimpleNamespace(name="physical"),
            effect_chance=None,
        )
        saved = SimpleNamespace(name="tackle")
        move_repository_mock.save.return_value = saved
        service = MoveService(repository=move_repository_mock, client=client)

        result = await service.get_or_create(
            resource={"url": "https://pokeapi.co/api/v2/move/33/"}
        )

        assert result is saved
        saved_entity = move_repository_mock.save.await_args.kwargs["entity"]
        assert saved_entity.order == 33
        assert saved_entity.power == 0
        assert saved_entity.accuracy == 0
