from __future__ import annotations

from datetime import datetime

from app.domain.progression.business import build_initial_attributes
from app.models.common import utcnow
from app.models.pokemon import Pokemon


def build_initial_pokedex_attributes(base_pokemon: Pokemon) -> dict[str, int]:
    return build_initial_attributes(base_pokemon)


def resolve_discovery_state(
    *,
    base_pokemon_name: str,
    discovered_pokemon_name: str | None,
    discovered_at: datetime | None = None,
) -> tuple[bool, datetime | None]:
    if discovered_pokemon_name is None or base_pokemon_name != discovered_pokemon_name:
        return False, None

    return True, discovered_at or utcnow()
