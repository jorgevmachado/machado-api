from types import SimpleNamespace
from app.domain.trainer.my_pokemon.move.business import select_initial_moves


def test_select_initial_moves_samples_when_more_than_four():
    moves = [
        SimpleNamespace(name="move1", deleted_at=None),
        SimpleNamespace(name="move2", deleted_at=None),
        SimpleNamespace(name="move3", deleted_at=None),
        SimpleNamespace(name="move4", deleted_at=None),
        SimpleNamespace(name="move5", deleted_at=None),
    ]
    result = select_initial_moves(moves)
    assert len(result) == 4
    assert all(move.name in [m.name for m in moves] for move in result)


def test_select_initial_moves_returns_filtered_unique_moves_when_four_or_less():
    moves = [
        SimpleNamespace(name="tackle", deleted_at=None),
        SimpleNamespace(name="tackle", deleted_at=None),
        SimpleNamespace(name="ember", deleted_at=None),
        SimpleNamespace(name="scratch", deleted_at="2026-01-01"),
        SimpleNamespace(name="growl", deleted_at=None),
    ]

    result = select_initial_moves(moves)

    assert [move.name for move in result] == ["tackle", "ember", "growl"]


def test_select_initial_moves_returns_empty_list_when_all_moves_are_deleted():
    moves = [
        SimpleNamespace(name="tackle", deleted_at="2026-01-01"),
        SimpleNamespace(name="ember", deleted_at="2026-01-01"),
    ]

    result = select_initial_moves(moves)

    assert result == []

