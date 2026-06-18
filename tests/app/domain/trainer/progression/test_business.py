from __future__ import annotations

from types import SimpleNamespace

from app.domain.trainer.progression.business import (
    _calculate_experience,
    _level_from_experience,
    calculate_attribute,
    calculate_progression,
    build_initial_attributes,
)


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


def test_calculate_progression_returns_none_without_growth_rate() -> None:
    result = calculate_progression(
        hp=10,
        level=5,
        speed=10,
        attack=10,
        defense=10,
        max_hp=10,
        experience=100,
        special_attack=10,
        special_defense=10,
        opponent_level=5,
        opponent_fainted=False,
        opponent_base_experience=100,
        growth_rate=None,
    )

    assert result is None


def test_calculate_progression_without_faint_keeps_level_and_experience() -> None:
    growth_rate = SimpleNamespace(formula="4 * level")

    result = calculate_progression(
        hp=20,
        level=5,
        speed=11,
        attack=12,
        defense=13,
        max_hp=25,
        experience=77,
        special_attack=14,
        special_defense=15,
        opponent_level=6,
        opponent_fainted=False,
        opponent_base_experience=80,
        growth_rate=growth_rate,
    )

    assert result is not None
    assert result.level == 5
    assert result.experience == 77
    assert result.level_up is False


def test_calculate_progression_with_faint_and_level_up_updates_attributes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.domain.trainer.progression.business._level_from_experience",
        lambda **_: 6,
    )
    growth_rate = SimpleNamespace(formula="x")

    result = calculate_progression(
        hp=50,
        level=5,
        speed=12,
        attack=13,
        defense=14,
        max_hp=51,
        experience=100,
        special_attack=15,
        special_defense=16,
        opponent_level=14,
        opponent_fainted=True,
        opponent_base_experience=200,
        growth_rate=growth_rate,
    )

    assert result is not None
    assert result.experience > 100
    assert result.level_up is True
    assert result.level == 6
    assert result.hp != 50
    assert result.max_hp != 51


def test_calculate_experience_and_calculate_attribute_helpers() -> None:
    assert _calculate_experience(level=1, base_experience=80) == 80
    assert _calculate_experience(level=14, base_experience=80) == 160
    assert calculate_attribute(base=50, level=10) == 15


def test_level_from_experience_stops_when_threshold_is_greater(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.trainer.progression.business.calculate_by_formula",
        lambda *_: 200,
    )
    assert _level_from_experience(level=7, formula="x", experience=100) == 7


def test_level_from_experience_loops_before_stopping(monkeypatch) -> None:
    values = iter([50, 300])
    monkeypatch.setattr(
        "app.domain.trainer.progression.business.calculate_by_formula",
        lambda *_: next(values),
    )
    assert _level_from_experience(level=7, formula="x", experience=100) == 7
