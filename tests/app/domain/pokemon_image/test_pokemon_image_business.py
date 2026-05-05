from app.domain.pokemon.image.business import (
    ensure_image,
    ensure_other_image,
    get_image_source,
    get_list_images,
)


def test_ensure_other_image_returns_group_source_url():
    other = {
        "official-artwork": {
            "front_default": "https://img.test/official.png",
        },
    }

    assert (
        ensure_other_image("official-artwork", "front_default", other)
        == "https://img.test/official.png"
    )


def test_ensure_image_uses_first_available_group():
    other = {
        "home": {
            "front_default": "https://img.test/home.png",
        },
        "official-artwork": {
            "front_default": "https://img.test/official.png",
        },
    }

    assert ensure_image("front_default", other) == "https://img.test/home.png"


def test_get_image_source_prefers_top_level_default_image():
    result = get_image_source(
        source="front",
        sprites={
            "front_default": "https://img.test/front.png",
            "other": {
                "official-artwork": {
                    "front_default": "https://img.test/official.png",
                },
            },
        },
    )

    assert result.source == "front_default"
    assert result.image == "https://img.test/front.png"


def test_get_image_source_falls_back_to_other_group():
    result = get_image_source(
        source="front",
        sprites={
            "other": {
                "official-artwork": {
                    "front_default": "https://img.test/official.png",
                },
            },
        },
    )

    assert result.source == "front_default"
    assert result.image == "https://img.test/official.png"


def test_get_list_images_collects_default_and_other_images():
    images = get_list_images(
        {
            "front_default": "https://img.test/front.png",
            "back_default": "https://img.test/back.png",
            "other": {
                "official-artwork": {
                    "front_default": "https://img.test/official.png",
                },
            },
        }
    )

    assert images == [
        "https://img.test/back.png",
        "https://img.test/front.png",
        "https://img.test/official.png",
    ]
