from __future__ import annotations

import random

from app.models.move import Move


def select_initial_moves(moves: list[Move]) -> list[Move]:
    unique_moves: list[Move] = []
    seen_names: set[str] = set()

    for move in moves:
        if move.deleted_at is not None or move.name in seen_names:
            continue
        seen_names.add(move.name)
        unique_moves.append(move)

    if len(unique_moves) <= 4:
        return unique_moves

    return random.sample(unique_moves, 4)
