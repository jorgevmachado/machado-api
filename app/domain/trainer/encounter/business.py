from __future__ import annotations

from collections.abc import Sequence

from app.models import Encounter


def resolve_initial_active_encounter(
    encounters: Sequence[Encounter],
) -> Encounter | None:
    if not encounters:
        return None
    return sorted(encounters, key=lambda encounter: encounter.order)[0]
