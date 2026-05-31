from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.domain.trainer.owned_pokemon.business import (
    rolled_capture_success,
    build_unique_owned_name,
    resolve_effective_nickname,
    slugify_name,
)


def _build_pokemon(capture_rate: int = 45) -> SimpleNamespace:
    return SimpleNamespace(name='bulbasaur', capture_rate=capture_rate)


def test_resolve_effective_nickname_prefers_trimmed_nickname() -> None:
    assert resolve_effective_nickname('bulbasaur', '  Leaf  ') == 'Leaf'


def test_resolve_effective_nickname_falls_back_to_pokemon_name() -> None:
    assert resolve_effective_nickname('bulbasaur', '   ') == 'bulbasaur'


def test_slugify_name_normalizes_unicode_and_symbols() -> None:
    assert slugify_name('Pikáchu!!!') == 'pikachu'
    assert slugify_name('###') == 'pokemon'


def test_build_unique_owned_name_appends_incremental_suffix() -> None:
    existing = {'pikachu', 'pikachu-2'}
    assert build_unique_owned_name('pikachu', existing) == 'pikachu-3'


def test_rolled_capture_success_returns_true_when_roll_within_chance() -> None:
    with patch('app.domain.trainer.owned_pokemon.business.random.randint', return_value=50):
        assert rolled_capture_success(50) is True


def test_rolled_capture_success_returns_false_when_roll_exceeds_chance() -> None:
    with patch('app.domain.trainer.owned_pokemon.business.random.randint', return_value=51):
        assert rolled_capture_success(50) is False
