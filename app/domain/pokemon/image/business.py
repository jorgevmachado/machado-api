from __future__ import annotations

from typing import cast

from app.domain.pokemon.image.schema import GetImageSourceResultSchema

PREFERRED_PRIMARY_IMAGES = (
    ("official-artwork", "front_default"),
    ("home", "front_default"),
    ("default", "front_default"),
)

DEFAULT_GROUPS = ["dream_world", "home", "official-artwork", "showdown", "default"]

DEFAULT_SOURCES = ["default", "shiny", "female"]

DEFAULT_IMAGES = [
    "back_default",
    "back_female",
    "back_shiny",
    "back_shiny_female",
    "front_default",
    "front_female",
    "front_shiny",
    "front_shiny_female",
]


def ensure_other_image(
    group: str,
    source: str,
    other: dict | None,
) -> str | None:
    if not other:
        return None

    origin = other.get(group)
    return origin.get(source) if origin else None


def ensure_image(
    source: str,
    other: dict | None,
    group: list[str] | None = None,
) -> str | None:
    if group is None:
        group = ["dream_world", "home", "official-artwork", "showdown"]

    if not other:
        return None

    current_image: str | None = None

    for item in group:
        image = ensure_other_image(item, source, other)
        if image:
            current_image = image
            break
    return current_image


def get_image_source(
    source: str,
    sprites: dict | None = None,
    group: list[str] | None = None,
    sources: list[str] | None = None,
    default: str | None = "default",
) -> GetImageSourceResultSchema:
    default_source = f"{source}_{default}"

    if sprites is None:
        return GetImageSourceResultSchema(source=default_source, image="")

    if sources is None:
        sources = DEFAULT_SOURCES

    default_image = sprites.get(default_source)

    if default_image:
        return GetImageSourceResultSchema(
            source=default_source, image=cast(str, default_image)
        )

    other = sprites.get("other")

    if other is None:
        return GetImageSourceResultSchema(source=default_source, image="")

    other_default_image = ensure_image(source=default_source, other=other, group=group)

    if other_default_image:
        return GetImageSourceResultSchema(
            source=default_source, image=other_default_image
        )

    other_source_image = ""
    for other_source in sources:
        other_default_source = f"{source}_{other_source}"
        other_default_source_image = ensure_image(
            source=other_default_source, other=other, group=group
        )
        if other_default_source_image:
            other_source_image = other_default_source_image
            break

    return GetImageSourceResultSchema(source=default_source, image=other_source_image)


def get_list_images(
    sprites: dict | None = None, groups: list[str] | None = None
) -> list[str]:
    if sprites is None:
        return []

    if groups is None:
        groups = DEFAULT_GROUPS

    images: list[str] = []
    images.extend(_ensure_list_image(sprites))

    other = sprites.get("other")
    if other:
        for item in groups:
            other_item = other.get(item)
            images.extend(_ensure_list_image(other_item) if other_item else [])

    return images


def _ensure_list_image(group: dict) -> list[str]:
    images: list[str] = []
    source_groups: list[str] = DEFAULT_IMAGES
    for source_group in source_groups:
        current_image = group.get(source_group)
        if current_image:
            images.append(cast(str, current_image))

    return images
