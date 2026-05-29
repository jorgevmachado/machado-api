from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.domain.trainer.owned_pokemon.business import (
    _rolled_capture_success,
    build_unique_owned_name,
    resolve_effective_nickname,
    slugify_name,
    validate_capture_rate,
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


def test_validate_capture_rate_skips_when_args_are_none() -> None:
    pokemon = _build_pokemon(capture_rate=100)
    validate_capture_rate(
        pokemon=pokemon,
        pokedex_hp=None,
        pokedex_max_hp=None,
        trainer_capture_rate=None,
    )


def test_validate_capture_rate_raises_when_trainer_rate_below_pokemon_rate() -> None:
    pokemon = _build_pokemon(capture_rate=150)
    with pytest.raises(HTTPException) as exc_info:
        validate_capture_rate(
            pokemon=pokemon,
            pokedex_hp=45,
            pokedex_max_hp=100,
            trainer_capture_rate=100,
        )
    assert exc_info.value.status_code == 400
    assert 'capture rate' in exc_info.value.detail


def test_validate_capture_rate_raises_when_pokemon_breaks_free() -> None:
    pokemon = _build_pokemon(capture_rate=45)
    with patch(
        'app.domain.trainer.owned_pokemon.business._rolled_capture_success',
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc_info:
            validate_capture_rate(
                pokemon=pokemon,
                pokedex_hp=100,
                pokedex_max_hp=100,
                trainer_capture_rate=255,
            )
        assert exc_info.value.status_code == 400
        assert 'broke free' in exc_info.value.detail


def test_validate_capture_rate_succeeds_when_roll_passes() -> None:
    pokemon = _build_pokemon(capture_rate=45)
    with patch(
        'app.domain.trainer.owned_pokemon.business._rolled_capture_success',
        return_value=True,
    ):
        validate_capture_rate(
            pokemon=pokemon,
            pokedex_hp=50,
            pokedex_max_hp=100,
            trainer_capture_rate=255,
        )


def test_rolled_capture_success_returns_true_when_roll_within_chance() -> None:
    with patch('app.domain.trainer.owned_pokemon.business.random.randint', return_value=50):
        assert _rolled_capture_success(50) is True


def test_rolled_capture_success_returns_false_when_roll_exceeds_chance() -> None:
    with patch('app.domain.trainer.owned_pokemon.business.random.randint', return_value=51):
        assert _rolled_capture_success(50) is False
