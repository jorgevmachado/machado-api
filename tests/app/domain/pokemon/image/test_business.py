from app.domain.pokemon.image.business import (
    ensure_image,
    ensure_other_image,
    get_image_source,
    get_list_images,
)


class TestImageBusiness:
    @staticmethod
    def test_ensure_other_image_returns_none_without_other() -> None:
        assert ensure_other_image("home", "front_default", None) is None

    @staticmethod
    def test_ensure_other_image_reads_group_source() -> None:
        other = {"home": {"front_default": "image-url"}}

        assert ensure_other_image("home", "front_default", other) == "image-url"

    @staticmethod
    def test_ensure_image_returns_first_available_group() -> None:
        other = {
            "dream_world": {"front_default": ""},
            "home": {"front_default": "home-url"},
        }

        assert ensure_image("front_default", other) == "home-url"

    @staticmethod
    def test_ensure_image_returns_none_when_other_is_missing() -> None:
        assert ensure_image("front_default", None) is None

    @staticmethod
    def test_get_image_source_returns_default_value_when_sprites_missing() -> None:
        result = get_image_source("front", None)

        assert result.source == "front_default"
        assert result.image == ""

    @staticmethod
    def test_get_image_source_reads_direct_sprite_field() -> None:
        result = get_image_source("front", {"front_default": "front-url"})

        assert result.image == "front-url"

    @staticmethod
    def test_get_image_source_falls_back_to_other_sources() -> None:
        sprites = {
            "other": {
                "official-artwork": {
                    "front_shiny": "front-shiny-url",
                }
            }
        }

        result = get_image_source("front", sprites=sprites)

        assert result.source == "front_default"
        assert result.image == "front-shiny-url"

    @staticmethod
    def test_get_image_source_returns_empty_when_other_group_is_missing() -> None:
        result = get_image_source("front", sprites={"front_shiny": "unused"})

        assert result.source == "front_default"
        assert result.image == ""

    @staticmethod
    def test_get_image_source_returns_other_default_image_when_available() -> None:
        sprites = {
            "other": {
                "home": {"front_default": "home-front-url"},
            }
        }

        result = get_image_source("front", sprites=sprites)

        assert result.source == "front_default"
        assert result.image == "home-front-url"

    @staticmethod
    def test_get_list_images_returns_empty_without_sprites() -> None:
        assert get_list_images(None) == []

    @staticmethod
    def test_get_list_images_collects_main_and_other_images() -> None:
        sprites = {
            "front_default": "front-url",
            "back_default": "back-url",
            "other": {
                "home": {"front_default": "home-front-url"},
                "official-artwork": {"front_default": "art-front-url"},
            },
        }

        result = get_list_images(sprites)

        assert "front-url" in result
        assert "back-url" in result
        assert "home-front-url" in result
        assert "art-front-url" in result
