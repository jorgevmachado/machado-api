from types import SimpleNamespace

from app.domain.trainer.my_pokemon.schema import MyPokemonSchema


def test_filter_active_moves_returns_value_unchanged_when_input_is_not_a_list():
    sentinel = object()

    result = MyPokemonSchema.filter_active_moves(sentinel)

    assert result is sentinel


def test_filter_active_moves_keeps_only_non_deleted_items_with_resource():
    move_kept = SimpleNamespace(deleted_at=None, pokemon_move=object())
    move_deleted = SimpleNamespace(deleted_at="2026-05-20", pokemon_move=object())
    move_without_resource = SimpleNamespace(deleted_at=None, pokemon_move=None)

    result = MyPokemonSchema.filter_active_moves(
        [move_kept, move_deleted, move_without_resource]
    )

    assert result == [move_kept]


