from __future__ import annotations

from http import HTTPStatus

from fastapi import HTTPException

MAX_PARTY_SIZE = 6


def validate_party_selection(my_pokemon_ids: list) -> None:
    if len(my_pokemon_ids) > MAX_PARTY_SIZE:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Trainer party cannot exceed {MAX_PARTY_SIZE} Pokemon",
        )
    if len(set(my_pokemon_ids)) != len(my_pokemon_ids):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Trainer party cannot contain duplicate Pokemon",
        )
