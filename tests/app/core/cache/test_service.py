import logging
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi_pagination import LimitOffsetPage
from pydantic import BaseModel, ConfigDict

from app.core.cache.manager import CacheManager
from app.core.cache.service import CacheService
from app.core.logging import LoggingParams
from app.shared.schemas import FilterPage


class BaseModelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    value: int


MOCK_ITEM = BaseModelSchema(id='mock_id', name='mock_name', value=42)


@pytest_asyncio.fixture
async def cache_service(redis_client):
    class TestableCacheService(CacheService):
        def __init__(self, logger_params, alias, prefix, redis_client):
            super().__init__(logger_params=logger_params, schema_class=BaseModelSchema)
            self.alias = alias
            self.prefix = prefix
            self.cache = CacheManager(redis_client=redis_client)

    return TestableCacheService(
        logger_params=LoggingParams(
            logger=logging.getLogger(__name__),
            service='cache_service',
            operation='test_cache',
        ),
        redis_client=redis_client,
        alias='test_cache',
        prefix='test_cache',
    )


class TestCacheServiceBuildKeyList:
    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_build_key_list(cache_service):
        page_filter = FilterPage(offset=0, limit=10)
        key = cache_service.build_key_list(page_filter)
        assert key.startswith(f'{cache_service.prefix}:list')


class TestCacheServiceGetList:
    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_get_list_return_none_when_cache_misses(cache_service):
        page_filter = FilterPage(offset=0, limit=10)
        key = cache_service.build_key_list(page_filter)
        result = await cache_service.get_list(key)
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_and_get_list(cache_service):
        list_item = [MOCK_ITEM]
        page_filter = FilterPage(offset=0, limit=10)
        key = cache_service.build_key_list(page_filter)
        await cache_service.set_list(key, list_item)
        result = await cache_service.get_list(key)
        assert isinstance(result, list)
        assert len(result) == len(list_item)

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_get_list_skips_non_dict_entries(cache_service):
        key = 'test_cache:list:test'
        total_result = 2
        cached_data = {
            'type': 'list',
            'data': [
                {
                    'id': '1',
                    'name': 'bulbasaur',
                    'value': 1,
                },
                'not_a_dict',
                {
                    'id': '2',
                    'name': 'ivysaur',
                    'value': 2,
                },
            ],
        }
        cache_service.cache.get_cache = AsyncMock(return_value=cached_data)
        result = await cache_service.get_list(key)
        assert isinstance(result, list)
        assert len(result) == total_result
        assert all(isinstance(p, BaseModelSchema) for p in result)

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_get_list_paginate_type(cache_service):
        key = 'test_cache:list:paginate'
        page_obj = LimitOffsetPage[BaseModelSchema](
            items=[MOCK_ITEM],
            limit=10,
            offset=0,
            total=1,
        )
        cached_data = {'type': 'paginate', 'data': page_obj.model_dump(mode='json')}
        cache_service.cache.get_cache = AsyncMock(return_value=cached_data)
        result = await cache_service.get_list(key)
        assert isinstance(result, LimitOffsetPage)
        assert result.total == 1

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_get_list_returns_none_for_invalid_cached_schema(cache_service):
        key = 'test_cache:list:custom-paginate'
        cached_data = {
            'type': 'custom-paginate',
            'data': {
                'items': [
                    {
                        'id': '1',
                        'name': 'bulbasaur',
                    }
                ],
                'meta': {
                    'total': 1,
                    'limit': 10,
                    'offset': 0,
                    'next_page': None,
                    'previous_page': None,
                    'total_pages': 1,
                    'current_page': 1,
                },
            },
        }
        cache_service.cache.get_cache = AsyncMock(return_value=cached_data)

        result = await cache_service.get_list(key)

        assert result is None


class TestCacheServiceSetList:
    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_list_paginate(cache_service):
        key = f'{cache_service.prefix}:list:paginate'
        page_obj = LimitOffsetPage[BaseModelSchema](
            items=[MOCK_ITEM],
            limit=10,
            offset=0,
            total=1,
        )

        cache_service.cache.set_cache = AsyncMock(return_value=None)
        result = await cache_service.set_list(key, page_obj)
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_all_list(cache_service):
        key = f'{cache_service.prefix}:list'

        cache_service.cache.set_cache = AsyncMock(return_value=None)
        result = await cache_service.set_list(key, [MOCK_ITEM])
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_all_list_with_ttl(cache_service):
        key = f'{cache_service.prefix}:list'

        cache_service.cache.set_cache = AsyncMock(return_value=None)
        result = await cache_service.set_list(key, [MOCK_ITEM], 400)
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_list_invalid_type(cache_service):
        key = f'{cache_service.prefix}:list'
        invalid_data = object()
        cache_service.cache.set_cache = AsyncMock(return_value=None)
        result = await cache_service.set_list(key, invalid_data)
        assert result is None


class TestCacheServiceBuildKeyOne:
    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_build_key_one(cache_service):
        key = cache_service.build_key_one('one')
        assert key.startswith(f'{cache_service.prefix}:one')


class TestCacheServiceGetOne:
    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_get_one_returns_none_when_cache_misses(
        cache_service,
    ):
        key = 'test_cache:name'
        result = await cache_service.get_one(key)
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_get_one_returns_schema(cache_service):
        key = 'test_cache:name'
        await cache_service.set_one(key, MOCK_ITEM)
        result = await cache_service.get_one(key)
        assert isinstance(result, BaseModelSchema)


class TestCacheServiceSetOne:
    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_one(cache_service):
        key = 'test_cache:name'
        cache_service.cache.set_cache = AsyncMock(return_value=None)
        result = await cache_service.set_one(key, MOCK_ITEM)
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_one_with_ttl(cache_service):
        key = 'test_cache:name'
        cache_service.cache.set_cache = AsyncMock(return_value=None)
        result = await cache_service.set_one(key, MOCK_ITEM, 300)
        assert result is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_cache_service_set_one_when_not_received_data(cache_service):
        key = 'test_cache:name'
        cache_service.cache.set_cache = AsyncMock(return_value=None)
        result = await cache_service.set_one(key, None)
        assert result is None
