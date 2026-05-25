from datetime import datetime, timezone
from types import SimpleNamespace

from app.domain.trainer.pokedex.business import (
    build_initial_pokedex_attributes,
    resolve_discovery_state,
)


def test_build_initial_pokedex_attributes_delegates_to_progression(monkeypatch):
    rolls = iter([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    monkeypatch.setattr(
        "app.domain.trainer.progression.business.random.uniform",
        lambda _min, _max: next(rolls),
    )
    base_pokemon = SimpleNamespace(
        hp=45,
        attack=49,
        defense=49,
        speed=45,
        special_attack=65,
        special_defense=65,
    )

    result = build_initial_pokedex_attributes(base_pokemon)

    assert result == {
        "level": 1,
        "experience": 0,
        "hp": 50,
        "max_hp": 50,
        "attack": 49,
        "defense": 49,
        "special_attack": 65,
        "special_defense": 65,
        "speed": 45,
    }


def test_resolve_discovery_state_returns_false_when_no_match():
    discovered, discovered_at = resolve_discovery_state(
        base_pokemon_name="bulbasaur",
        discovered_pokemon_name="charmander",
    )

    assert discovered is False
    assert discovered_at is None


def test_resolve_discovery_state_uses_given_timestamp():
    timestamp = datetime.now(timezone.utc)

    discovered, discovered_at = resolve_discovery_state(
        base_pokemon_name="bulbasaur",
        discovered_pokemon_name="bulbasaur",
        discovered_at=timestamp,
    )

    assert discovered is True
    assert discovered_at is timestamp


def test_resolve_discovery_state_generates_timestamp_when_missing():
    discovered, discovered_at = resolve_discovery_state(
        base_pokemon_name="bulbasaur",
        discovered_pokemon_name="bulbasaur",
    )

    assert discovered is True
    assert discovered_at is not None
