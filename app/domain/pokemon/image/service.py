from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService
from app.domain.pokemon.image.business import get_image_source, get_list_images
from app.domain.pokemon.image.repository import PokemonImageRepository
from app.domain.pokemon.image.schema import PokemonImageSchema
from app.models import PokemonImage

logger = logging.getLogger(__name__)


class PokemonImageService(BaseService[PokemonImageRepository, PokemonImage]):
    def __init__(self, repository: PokemonImageRepository) -> None:
        super().__init__(
            alias="PokemonImage",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service="PokemonImageService", operation="image"
            ),
            schema_class=PokemonImageSchema,
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(PokemonImageRepository(session))

    async def sync_from_sprites(
        self, order: int, sprites: dict | None
    ) -> PokemonImage | None:
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
            entity=PokemonImage(
                order=order,
                images=images,
                back_image=back_image,
                front_image=front_image,
                back_source=back_source,
                front_source=front_source,
            )
        )
