from __future__ import annotations

from app.core.repository.base import BaseRepository
from app.models.__DOMAIN_ENTITY__ import __CLASS_NAME__


class __CLASS_NAME__Repository(BaseRepository[__CLASS_NAME__]):
    model = __CLASS_NAME__
