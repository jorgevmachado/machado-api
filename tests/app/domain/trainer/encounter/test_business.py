from __future__ import annotations

from types import SimpleNamespace

from app.domain.trainer.encounter.business import resolve_initial_active_encounter


def test_resolve_initial_active_encounter_returns_none_for_empty() -> None:
    assert resolve_initial_active_encounter([]) is None


def test_resolve_initial_active_encounter_returns_lowest_order() -> None:
    result = resolve_initial_active_encounter(
        [
            SimpleNamespace(order=3, id="c"),
            SimpleNamespace(order=1, id="a"),
            SimpleNamespace(order=2, id="b"),
        ]
    )
    assert result.id == "a"
