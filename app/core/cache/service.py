from typing import Annotated, Optional, Type, TypeVar

from fastapi import Query
from fastapi_pagination import LimitOffsetPage
from pydantic import BaseModel, ValidationError

from app.core.cache.manager import CacheManager
from app.core.logging import LoggingParams, log_service_exception, log_service_success
from app.core.pagination.schemas import CustomLimitOffsetPage
from app.shared.schemas import FilterPage

SchemaT = TypeVar('SchemaT', bound=BaseModel)


class CacheService:
    def __init__(
        self,
        *,
        alias: str = 'default',
        prefix: str = 'cache',
        logger_params: LoggingParams,
        schema_class: Type[SchemaT],
        default_ttl: int = 86400,
    ):
        self.alias = alias
        self.prefix = prefix
        self.logger_params = logger_params
        self.schema_class = schema_class
        self.ttl = default_ttl
        self.cache = CacheManager()

    def build_key_list(
        self,
        page_filter: Annotated[FilterPage, Query()] = None,
    ):
        filter_page = FilterPage.build(page_filter)
        log_service_success(
            self.logger_params,
            operation='cache_build_key_list',
            message=f'The {self.alias} list cache key was successfully created.',
        )
        return self.cache.build_key(self.prefix, 'list', filter_page.model_dump())

    async def get_list(
        self, key: str
    ) -> list[SchemaT] | LimitOffsetPage[SchemaT] | CustomLimitOffsetPage[SchemaT] | None:
        cached = await self.cache.get_cache(key)
        try:
            if cached and 'type' in cached and cached['type'] == 'list':
                list_deserialized: list[SchemaT] = []
                for item in cached['data']:
                    if not isinstance(item, dict):
                        continue
                    list_deserialized.append(self.schema_class.model_validate(item))
                log_service_success(
                    self.logger_params,
                    operation='cache_get_list',
                    message=f'List of {self.alias} stored in cache.',
                )
                return list_deserialized
            if cached and 'type' in cached and cached['type'] == 'paginate':
                log_service_success(
                    self.logger_params,
                    operation='cache_get_list',
                    message=f'Paginated list of cached {self.alias}',
                )
                return LimitOffsetPage[self.schema_class].model_validate(cached['data'])
            if cached and 'type' in cached and cached['type'] == 'custom-paginate':
                log_service_success(
                    self.logger_params,
                    operation='cache_get_list',
                    message=f'Custom paginated list of cached {self.alias}',
                )
                return CustomLimitOffsetPage[self.schema_class].model_validate(cached['data'])
        except ValidationError:
            log_service_exception(
                self.logger_params,
                operation='cache_get_list',
                message=f'Cached {self.alias} data is invalid for the current schema. Ignoring cache.',
            )
            return None
        log_service_success(
            self.logger_params,
            operation='cache_get_list',
            message=f'No {self.alias} data is cached.',
        )

        return None

    async def set_list(
        self,
        key: str,
        data: list[SchemaT] | LimitOffsetPage[SchemaT] | CustomLimitOffsetPage[SchemaT],
        ttl: Optional[int] = None,
    ) -> None:
        cache_ttl = ttl or self.ttl
        if isinstance(data, list):
            list_serialized = [
                self.schema_class.model_validate(item).model_dump(mode='json') for item in data
            ]
            await self.cache.set_cache(
                key, {'type': 'list', 'data': list_serialized}, cache_ttl
            )
            log_service_success(
                self.logger_params,
                operation='cache_set_list',
                message=f'List of {self.alias} successfully cached.',
            )
            return None
        if isinstance(data, LimitOffsetPage):
            list_serialized = (
                LimitOffsetPage[self.schema_class].model_validate(data).model_dump(mode='json')
            )
            await self.cache.set_cache(
                key, {'type': 'paginate', 'data': list_serialized}, cache_ttl
            )
            log_service_success(
                self.logger_params,
                operation='cache_set_list',
                message=f'Paginated list of {self.alias} successfully cached.',
            )
            return None
        if isinstance(data, CustomLimitOffsetPage):
            list_serialized = (
                CustomLimitOffsetPage[self.schema_class]
                .model_validate(data)
                .model_dump(mode='json')
            )
            await self.cache.set_cache(
                key, {'type': 'custom-paginate', 'data': list_serialized}, cache_ttl
            )
            log_service_success(
                self.logger_params,
                operation='cache_set_list',
                message=f'Custom paginated list of {self.alias} successfully cached.',
            )
            return None

        log_service_success(
            self.logger_params,
            operation='cache_set_list',
            message=f'No {self.alias} data was cached.',
        )
        return None

    def build_key_one(self, param: str) -> str:
        log_service_success(
            self.logger_params,
            operation='cache_build_key_one',
            message=f'The {self.alias} single item cache key was successfully created.',
        )
        return self.cache.build_key(self.prefix, param)

    async def get_one(self, key: str) -> SchemaT | None:
        cached = await self.cache.get_cache(key)
        if cached:
            log_service_success(
                self.logger_params,
                operation='cache_get_one',
                message=f'{self.alias} {key} stored in cache',
            )
            return self.schema_class.model_validate(cached)
        log_service_success(
            self.logger_params,
            operation='cache_get_one',
            message=f'No {self.alias} {key} data is cached.',
        )
        return None

    async def set_one(
        self, key: str, data: Optional[SchemaT] = None, ttl: Optional[int] = None
    ) -> None:
        cache_ttl = ttl or self.ttl
        if not data:
            log_service_exception(
                self.logger_params,
                operation='cache_set_one',
                message=f'{self.alias} {key} not provided for caching',
            )
            return None
        serialized = self.schema_class.model_validate(data).model_dump(mode='json')
        await self.cache.set_cache(key, serialized, cache_ttl)
        log_service_success(
            self.logger_params,
            operation='cache_set_one',
            message=f'{self.alias} {key} successfully cached.',
        )
        return None
