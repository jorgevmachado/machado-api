from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

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
            alias='Image',
            repository=repository,
            logger_params=LoggingParams(
                logger=logger, service='ImageService', operation='pokemon.image'
            ),
            schema_class=ImageSchema,
            cache_prefix='image',
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(ImageRepository(session))
