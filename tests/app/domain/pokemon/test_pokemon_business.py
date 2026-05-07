from app.domain.pokemon.business import (
    build_external_image,
    format_pokemon_image_order,
)
from app.shared.utils.number import ensure_order_number


def test_ensure_order_number_from_url():
    assert ensure_order_number("https://pokeapi.co/api/v2/pokemon/25/") == 25


def test_format_pokemon_image_order_uses_four_digits():
    assert format_pokemon_image_order("01") == "001"
    assert format_pokemon_image_order(25) == "025"
    assert format_pokemon_image_order(1000) == "1000"


def test_build_external_image():
    assert build_external_image(25).endswith("/025.png")
