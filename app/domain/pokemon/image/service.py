from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.image.business import get_image_source, get_list_images

from app.domain.pokemon.image.repository import ImageRepository
from app.domain.pokemon.image.schema import (
    ImageSchema,
)
from app.models import Image

logger = logging.getLogger(__name__)


class ImageService(BaseService[ImageRepository, Image]):
    def __init__(
        self,
        repository: ImageRepository,
    ) -> None:
        super().__init__(
            alias="Image",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="ImageService", operation="pokemon.image"
            ),
            schema_class=ImageSchema,
            cache_prefix="image",
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(ImageRepository(session))

    async def sync_from_sprites(self, order: int, sprites: dict | None) -> Image | None:

        entity = await self.repository.find_by(order=order)
        if entity:
            return entity

        if not sprites:
            return None

        front_image_source = get_image_source(source="front", sprites=sprites)
        front_source = front_image_source.source
        front_image = front_image_source.image

        back_image_source = get_image_source(source="back", sprites=sprites)
        back_source = back_image_source.source
        back_image = back_image_source.image

        images: list[str] = get_list_images(sprites=sprites)

        return await self.repository.save(
            entity=Image(
                order=order,
                images=images,
                back_image=back_image,
                front_image=front_image,
                back_source=back_source,
                front_source=front_source,
            )
        )
