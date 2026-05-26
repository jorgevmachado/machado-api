from __future__ import annotations

from app.models import MyPokemon


def build_healing_log_payload(
    *,
    my_pokemon: MyPokemon,
    restored_hp: int,
    restored_pp: int,
    was_revived: bool,
) -> dict[str, int | bool | str]:
    return {
        "pokemon_name": my_pokemon.name,
        "pokemon_nickname": my_pokemon.nickname,
        "restored_hp": restored_hp,
        "restored_pp": restored_pp,
        "was_revived": was_revived,
    }


def resolve_healing_action_type(*, was_revived: bool) -> str:
    return "REVIVE_AND_HEAL" if was_revived else "FULL_HEAL"
