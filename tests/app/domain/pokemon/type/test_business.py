from app.domain.pokemon.type.business import (
    ensure_badges,
    ensure_colors,
    ensure_damage_relations,
)


class TestTypeBusiness:
    @staticmethod
    def test_ensure_colors_returns_default_when_name_is_missing() -> None:
        result = ensure_colors(None)

        assert result.name == "default"
        assert result.text_color == "#fff"

    @staticmethod
    def test_ensure_colors_returns_known_color() -> None:
        result = ensure_colors("grass")

        assert result.name == "grass"
        assert result.background_color == "#9bcc50"

    @staticmethod
    def test_ensure_badges_returns_default_when_sprites_missing() -> None:
        result = ensure_badges(None)

        assert "generation-viii" in result.badge_url

    @staticmethod
    def test_ensure_badges_returns_default_when_generation_group_is_missing() -> None:
        result = ensure_badges({"generation-vii": {}})

        assert "generation-viii" in result.badge_url

    @staticmethod
    def test_ensure_badges_extracts_custom_values_and_fallbacks() -> None:
        sprites = {
            "generation-viii": {
                "brilliant-diamond-shining-pearl": {
                    "name_icon": "badge-url",
                    "symbol_icon": "badge-icon-url",
                },
                "sword-shield": {
                    "name_icon": "shield-url",
                    "symbol_icon": "shield-icon-url",
                },
                "legends-arceus": {
                    "name_icon": "legend-url",
                    "symbol_icon": "legend-icon-url",
                },
            }
        }

        result = ensure_badges(sprites)

        assert result.badge_url == "badge-url"
        assert result.badge_icon_url == "badge-icon-url"
        assert result.badge_shield_url == "shield-url"
        assert result.badge_shield_icon_url == "shield-icon-url"
        assert result.badge_legends_url == "legend-url"
        assert result.badge_legend_icon_url == "legend-icon-url"

    @staticmethod
    def test_ensure_damage_relations_handles_empty_payload() -> None:
        result = ensure_damage_relations(None)

        assert result is not None
        assert result.weaknesses == []
        assert result.strengths == []

    @staticmethod
    def test_ensure_damage_relations_extracts_valid_named_resources() -> None:
        damage_relations = {
            "double_damage_from": [
                {"name": "water", "url": "https://pokeapi.co/api/v2/type/11/"},
                {"name": "invalid"},
            ],
            "half_damage_from": [],
            "double_damage_to": [
                {"name": "fire", "url": "https://pokeapi.co/api/v2/type/10/"},
            ],
            "half_damage_to": [None],
        }

        result = ensure_damage_relations(damage_relations)

        assert result is not None
        assert [item.name for item in result.weaknesses] == ["water"]
        assert [item.name for item in result.strengths] == ["fire"]
