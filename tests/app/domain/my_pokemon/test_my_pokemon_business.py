from types import SimpleNamespace

from app.domain.my_pokemon.business import (
    build_unique_owned_name,
    resolve_effective_nickname,
    select_initial_moves,
)
from app.domain.progression.business import build_initial_attributes


def test_resolve_effective_nickname_falls_back_to_base_name():
    assert resolve_effective_nickname("bulbasaur", "   ") == "bulbasaur"


def test_build_unique_owned_name_appends_suffix_when_needed():
    assert build_unique_owned_name("charizard", {"charizard", "charizard-2"}) == (
        "charizard-3"
    )


def test_select_initial_moves_keeps_distinct_moves_and_limits_to_four(monkeypatch):
    moves = [
        SimpleNamespace(name="scratch", deleted_at=None),
        SimpleNamespace(name="growl", deleted_at=None),
        SimpleNamespace(name="ember", deleted_at=None),
        SimpleNamespace(name="smokescreen", deleted_at=None),
        SimpleNamespace(name="slash", deleted_at=None),
        SimpleNamespace(name="ember", deleted_at=None),
    ]
    monkeypatch.setattr(
        "app.domain.my_pokemon.business.random.sample",
        lambda values, limit: values[:limit],
    )

    selected = select_initial_moves(moves)

    assert [move.name for move in selected] == [
        "scratch",
        "growl",
        "ember",
        "smokescreen",
    ]


def test_build_initial_attributes_uses_base_stats(monkeypatch):
    rolls = iter([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    monkeypatch.setattr(
        "app.domain.progression.business.random.uniform",
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

    result = build_initial_attributes(base_pokemon)

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
