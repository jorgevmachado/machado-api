from typing import Any, cast

from app.domain.pokemon.type.schema import (
    PokemonTypeColorSchema,
    PokemonTypeBadgeSchema,
    EnsureDamageRelationsResultSchema,
)
from app.infrastructure.external_api.schemas import NamedExternalResourceSchema

TYPE_COLORS = [
    PokemonTypeColorSchema(
        id=1, name="ice", text_color="#fff", background_color="#51c4e7"
    ),
    PokemonTypeColorSchema(
        id=2, name="bug", text_color="#b5d7a7", background_color="#482d53"
    ),
    PokemonTypeColorSchema(
        id=3, name="fire", text_color="#fff", background_color="#fd7d24"
    ),
    PokemonTypeColorSchema(
        id=4, name="rock", text_color="#fff", background_color="#a38c21"
    ),
    PokemonTypeColorSchema(
        id=5, name="dark", text_color="#fff", background_color="#707070"
    ),
    PokemonTypeColorSchema(
        id=6, name="steel", text_color="#fff", background_color="#9eb7b8"
    ),
    PokemonTypeColorSchema(
        id=7, name="ghost", text_color="#fff", background_color="#7b62a3"
    ),
    PokemonTypeColorSchema(
        id=8, name="fairy", text_color="#cb3fa0", background_color="#c8a2c8"
    ),
    PokemonTypeColorSchema(
        id=9, name="water", text_color="#fff", background_color="#4592c4"
    ),
    PokemonTypeColorSchema(
        id=10, name="grass", text_color="#212121", background_color="#9bcc50"
    ),
    PokemonTypeColorSchema(
        id=11, name="normal", text_color="#000", background_color="#fff"
    ),
    PokemonTypeColorSchema(
        id=12, name="dragon", text_color="#fff", background_color="#FF8C00"
    ),
    PokemonTypeColorSchema(
        id=13, name="poison", text_color="#fff", background_color="#b97fc9"
    ),
    PokemonTypeColorSchema(
        id=14, name="flying", text_color="#424242", background_color="#3dc7ef"
    ),
    PokemonTypeColorSchema(
        id=15, name="ground", text_color="#f5f5f5", background_color="#bc5e00"
    ),
    PokemonTypeColorSchema(
        id=16, name="psychic", text_color="#fff", background_color="#f366b9"
    ),
    PokemonTypeColorSchema(
        id=17, name="electric", text_color="#212121", background_color="#eed535"
    ),
    PokemonTypeColorSchema(
        id=18, name="fighting", text_color="#fff", background_color="#d56723"
    ),
]


def ensure_colors(type_name: str | None = None) -> PokemonTypeColorSchema:
    default_type_color = PokemonTypeColorSchema(
        id=0,
        name=type_name if type_name else "default",
        text_color="#fff",
        background_color="#000",
    )

    if not type_name:
        return default_type_color

    pokemon_type_color = next(
        (color for color in TYPE_COLORS if color.name == type_name), default_type_color
    )

    return pokemon_type_color


def ensure_badges(
    sprites: dict[str, Any] | None,
    generation: str = "generation-viii",
    badge_name: str = "brilliant-diamond-shining-pearl",
    badge_shield_name: str = "sword-shield",
    badge_legend_name: str = "legends-arceus",
) -> PokemonTypeBadgeSchema:
    default_type_badges = PokemonTypeBadgeSchema(
        badge_url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/types/generation-viii/brilliant-diamond-shining-pearl/1.png",
        badge_icon_url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/types/generation-viii/brilliant-diamond-shining-pearl/small/1.png",
        badge_shield_url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/types/generation-viii/sword-shield/1.png",
        badge_legends_url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/types/generation-viii/legends-arceus/1.png",
        badge_legend_icon_url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/types/generation-viii/legends-arceus/small/1.png",
        badge_shield_icon_url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/types/generation-viii/sword-shield/small/1.png",
    )

    if not sprites:
        return default_type_badges

    badges = sprites.get(generation)

    if badges is not None:
        badge = badges.get(badge_name, {})
        badge_url = (
            badge.get("name_icon")
            if badge.get("name_icon")
            else default_type_badges.badge_url
        )
        badge_icon_url = (
            badge.get("symbol_icon")
            if badge.get("symbol_icon")
            else default_type_badges.badge_icon_url
        )

        badge_shield = badges.get(badge_shield_name, {})
        badge_shield_url = (
            badge_shield.get("name_icon")
            if badge_shield.get("name_icon")
            else default_type_badges.badge_shield_url
        )
        badge_shield_icon_url = (
            badge_shield.get("symbol_icon")
            if badge_shield.get("symbol_icon")
            else default_type_badges.badge_shield_icon_url
        )

        badge_legends = badges.get(badge_legend_name, {})
        badge_legends_url = (
            badge_legends.get("name_icon")
            if badge_legends.get("name_icon")
            else default_type_badges.badge_legends_url
        )
        badge_legend_icon_url = (
            badge_legends.get("symbol_icon")
            if badge_legends.get("symbol_icon")
            else default_type_badges.badge_legend_icon_url
        )

        return PokemonTypeBadgeSchema(
            badge_url=badge_url,
            badge_icon_url=badge_icon_url,
            badge_shield_url=badge_shield_url,
            badge_legends_url=badge_legends_url,
            badge_legend_icon_url=badge_legend_icon_url,
            badge_shield_icon_url=badge_shield_icon_url,
        )

    return default_type_badges


def ensure_damage_relations(
    damage_relations: dict[str, Any] | None,
) -> EnsureDamageRelationsResultSchema | None:
    if not damage_relations:
        return EnsureDamageRelationsResultSchema(weaknesses=[], strengths=[])

    weaknesses: list[NamedExternalResourceSchema] = []
    weaknesses.extend(
        _extract_damage_relations(damage_relations.get("double_damage_from", []))
    )
    weaknesses.extend(
        _extract_damage_relations(damage_relations.get("half_damage_from", []))
    )

    strengths: list[NamedExternalResourceSchema] = []
    strengths.extend(
        _extract_damage_relations(damage_relations.get("double_damage_to", []))
    )
    strengths.extend(
        _extract_damage_relations(damage_relations.get("half_damage_to", []))
    )

    return EnsureDamageRelationsResultSchema(weaknesses=weaknesses, strengths=strengths)


def _extract_damage_relations(
    damage_relations: list[dict[str, Any]] | None = None,
) -> list[NamedExternalResourceSchema]:
    if not damage_relations:
        return []

    return [
        extracted_relation
        for damage_relation in damage_relations
        if (extracted_relation := _extract_damage_relation(damage_relation)) is not None
    ]


def _extract_damage_relation(
    damage_relation: dict[str, Any] | None = None,
) -> NamedExternalResourceSchema | None:
    if not damage_relation:
        return None
    url: str = cast(str, damage_relation.get("url"))
    name: str = cast(str, damage_relation.get("name"))
    if url and name:
        return NamedExternalResourceSchema(url=url, name=name)
    return None
