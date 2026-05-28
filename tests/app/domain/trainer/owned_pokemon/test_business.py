from app.domain.trainer.owned_pokemon.business import (
    build_unique_owned_name,
    resolve_effective_nickname,
    slugify_name,
)


def test_resolve_effective_nickname_prefers_trimmed_nickname() -> None:
    assert resolve_effective_nickname("bulbasaur", "  Leaf  ") == "Leaf"


def test_resolve_effective_nickname_falls_back_to_pokemon_name() -> None:
    assert resolve_effective_nickname("bulbasaur", "   ") == "bulbasaur"


def test_slugify_name_normalizes_unicode_and_symbols() -> None:
    assert slugify_name("Pikáchu!!!") == "pikachu"
    assert slugify_name("###") == "pokemon"


def test_build_unique_owned_name_appends_incremental_suffix() -> None:
    existing = {"pikachu", "pikachu-2"}
    assert build_unique_owned_name("pikachu", existing) == "pikachu-3"
