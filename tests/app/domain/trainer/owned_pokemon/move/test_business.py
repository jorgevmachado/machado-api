from __future__ import annotations

from types import SimpleNamespace

from app.domain.trainer.owned_pokemon.move.business import select_initial_moves


def test_select_initial_moves_filters_deleted_and_duplicates() -> None:
    moves = [
        SimpleNamespace(name="tackle", deleted_at=None),
        SimpleNamespace(name="tackle", deleted_at=None),
        SimpleNamespace(name="growl", deleted_at=None),
        SimpleNamespace(name="scratch", deleted_at="deleted"),
    ]

    selected = select_initial_moves(moves)

    assert [move.name for move in selected] == ["tackle", "growl"]


def test_select_initial_moves_samples_when_more_than_four(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.trainer.owned_pokemon.move.business.random.sample",
        lambda values, amount: values[:amount],
    )
    moves = [
        SimpleNamespace(name=f"move-{index}", deleted_at=None) for index in range(6)
    ]

    selected = select_initial_moves(moves)

    assert len(selected) == 4
    assert selected[0].name == "move-0"
