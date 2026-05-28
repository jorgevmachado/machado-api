from __future__ import annotations

from types import SimpleNamespace

from app.domain.trainer.progression.business import build_initial_attributes


def test_build_initial_attributes_rolls_expected_stats(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.trainer.progression.business.random.uniform", lambda *_: 1.0
    )
    pokemon = SimpleNamespace(
        attack=49,
        defense=49,
        speed=45,
        special_attack=65,
        special_defense=65,
        hp=45,
    )

    result = build_initial_attributes(base_pokemon=pokemon)

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


def test_build_initial_attributes_applies_minimums(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.trainer.progression.business.random.uniform", lambda *_: 0.0
    )
    pokemon = SimpleNamespace(
        attack=0,
        defense=None,
        speed=0,
        special_attack=None,
        special_defense=0,
        hp=0,
    )

    result = build_initial_attributes(base_pokemon=pokemon)

    assert result["attack"] == 1
    assert result["defense"] == 1
    assert result["special_attack"] == 1
    assert result["special_defense"] == 1
    assert result["speed"] == 1
    assert result["hp"] == 10
