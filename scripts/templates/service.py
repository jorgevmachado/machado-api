from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import LoggingParams
from app.core.service.base import BaseService

from app.domain.__DOMAIN_MODULE__.repository import __CLASS_NAME__Repository
from app.domain.__DOMAIN_MODULE__.schema import (
    __CLASS_NAME__Schema,
)
from app.models import __CLASS_NAME__

logger = logging.getLogger(__name__)


class __CLASS_NAME__Service(BaseService[__CLASS_NAME__Repository, __CLASS_NAME__]):
    def __init__(
        self,
        repository: __CLASS_NAME__Repository,
    ) -> None:
        super().__init__(
            alias="__CLASS_NAME__",
            repository=repository,
            logger_params=LoggingParams(
                logger=logger,
                service="__CLASS_NAME__Service",
                operation="__DOMAIN_MODULE__",
            ),
            schema_class=__CLASS_NAME__Schema,
            cache_prefix="__DOMAIN_ENTITY__",
        )

    @classmethod
    def from_session(cls, session: AsyncSession):
        return cls(__CLASS_NAME__Repository(session))
