from __future__ import annotations

from fastapi_pagination import LimitOffsetPage

from app.core.pagination import CustomLimitOffsetPage
from app.domain.pokemon.schema import PokemonSchema


# Type aliases for cache serialization
PokemonListType = (
    list[PokemonSchema]
    | LimitOffsetPage[PokemonSchema]
    | CustomLimitOffsetPage[PokemonSchema]
)
SerializedCacheResult = dict | None

POKEMON_EXTERNAL_IMAGE_URL = "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/detail/{order}.png"


def format_pokemon_image_order(order: int | str) -> str:
    return str(int(order)).zfill(4)


def build_external_image(order: int | str) -> str:
    return POKEMON_EXTERNAL_IMAGE_URL.format(order=format_pokemon_image_order(order))


def first_english_flavor_text(entries: list[dict] | None) -> str | None:
    for entry in entries or []:
        language = entry.get("language") or {}
        if language.get("name") == "en":
            text = entry.get("flavor_text")
            return " ".join(text.split()) if text else None
    return None


def stats_by_name(payload: dict) -> dict[str, int]:
    return {
        stat["stat"]["name"].replace("-", "_"): stat["base_stat"]
        for stat in payload.get("stats", [])
    }


def result_list_cache_serialize(
    data: PokemonListType,
) -> SerializedCacheResult:
    if isinstance(data, list):
        list_serialized = [
            PokemonSchema.model_validate(pokemon).serialize() for pokemon in data
        ]
        return {"type": "list", "data": list_serialized}
    if isinstance(data, LimitOffsetPage):
        list_paginated_serialized: dict = (
            LimitOffsetPage[PokemonSchema].model_validate(data).model_dump(mode="json")
        )
        return {"type": "paginate", "data": list_paginated_serialized}
    if isinstance(data, CustomLimitOffsetPage):
        list_paginated_serialized: dict = (
            CustomLimitOffsetPage[PokemonSchema]
            .model_validate(data)
            .model_dump(mode="json")
        )
        return {"type": "custom-paginate", "data": list_paginated_serialized}
    return None


def result_cache_serialize(data: PokemonSchema) -> SerializedCacheResult:
    return PokemonSchema.model_validate(data).serialize()
