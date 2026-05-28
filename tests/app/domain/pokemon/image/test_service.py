from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.pokemon.image.service import ImageService


class TestImageService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_sprites_returns_existing_entity(
        image_repository_mock: AsyncMock,
    ) -> None:
        existing = SimpleNamespace(id="image-id")
        image_repository_mock.find_by.return_value = existing
        service = ImageService(repository=image_repository_mock)

        result = await service.sync_from_sprites(
            order=1, sprites={"front_default": "url"}
        )

        assert result is existing

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_sprites_returns_none_without_sprites(
        image_repository_mock: AsyncMock,
    ) -> None:
        service = ImageService(repository=image_repository_mock)

        result = await service.sync_from_sprites(order=1, sprites=None)

        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_from_sprites_saves_mapped_images(
        image_repository_mock: AsyncMock,
    ) -> None:
        saved = SimpleNamespace(id="saved-image-id")
        image_repository_mock.save.return_value = saved
        service = ImageService(repository=image_repository_mock)
        sprites = {
            "front_default": "front-url",
            "back_default": "back-url",
            "other": {"official-artwork": {"front_default": "art-front-url"}},
        }

        result = await service.sync_from_sprites(order=1, sprites=sprites)

        assert result is saved
        saved_entity = image_repository_mock.save.await_args.kwargs["entity"]
        assert saved_entity.order == 1
        assert saved_entity.front_image == "front-url"
        assert saved_entity.back_image == "back-url"
        assert "front-url" in saved_entity.images
