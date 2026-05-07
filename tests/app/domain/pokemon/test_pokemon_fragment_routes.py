from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.service.base import BaseService
from app.domain.pokemon.ability import route as ability_route
from app.domain.pokemon.encounter import route as encounter_route
from app.domain.pokemon.growth_rate import route as growth_rate_route
from app.domain.pokemon.habitat import route as habitat_route
from app.domain.pokemon.move import route as move_route
from app.domain.pokemon.type import route as type_route


ROUTE_CASES = [
    (
        ability_route.get_pokemon_ability_service,
        ability_route.get_pokemon_ability_filter,
        ability_route.list_pokemon_abilities,
        ability_route.get_pokemon_ability,
    ),
    (
        encounter_route.get_pokemon_encounter_service,
        encounter_route.get_pokemon_encounter_filter,
        encounter_route.list_pokemon_encounter,
        encounter_route.get_pokemon_encounter,
    ),
    (
        growth_rate_route.get_pokemon_growth_rate_service,
        growth_rate_route.get_pokemon_growth_rate_filter,
        growth_rate_route.list_pokemon_abilities,
        growth_rate_route.get_pokemon_growth_rate,
    ),
    (
        habitat_route.get_pokemon_habitat_service,
        habitat_route.get_pokemon_habitat_filter,
        habitat_route.list_pokemon_habitat,
        habitat_route.get_pokemon_habitat,
    ),
    (
        move_route.get_pokemon_move_service,
        move_route.get_pokemon_move_filter,
        move_route.list_pokemon_move,
        move_route.get_pokemon_move,
    ),
    (
        type_route.get_pokemon_type_service,
        type_route.get_pokemon_type_filter,
        type_route.list_pokemon_type,
        type_route.get_pokemon_type,
    ),
]


@pytest.mark.parametrize(
    "service_factory, filter_factory, _list_func, _get_func", ROUTE_CASES
)
def test_fragment_service_factory_and_filter(
    service_factory, filter_factory, _list_func, _get_func
):
    service = service_factory(AsyncMock())
    page_filter = filter_factory(page=1, offset=0, limit=12, name="name", order=1)

    assert isinstance(service, BaseService)
    assert page_filter.page == 1
    assert page_filter.name == "name"
    assert page_filter.order == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "_service_factory, filter_factory, list_func, get_func", ROUTE_CASES
)
async def test_fragment_route_handlers_delegate(
    _service_factory, filter_factory, list_func, get_func
):
    service = AsyncMock()
    expected_list = SimpleNamespace(items=[])
    expected_one = SimpleNamespace(name="item")
    service.list_all_cached.return_value = expected_list
    service.find_one_cached.return_value = expected_one
    page_filter = filter_factory(page=1, limit=12)

    list_result = await list_func(
        _=SimpleNamespace(id="user-id"),
        service=service,
        page_filter=page_filter,
    )
    get_result = await get_func(
        identifier="item",
        _=SimpleNamespace(id="user-id"),
        service=service,
    )

    assert list_result is expected_list
    assert get_result is expected_one
    service.list_all_cached.assert_awaited_once_with(page_filter=page_filter)
    service.find_one_cached.assert_awaited_once_with(param="item")
