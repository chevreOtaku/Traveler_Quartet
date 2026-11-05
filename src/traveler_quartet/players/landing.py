"""Where pawns land, computed from the board alone: two dice, and the square that sends you to the dungeon. The cards
that move a pawn are left out -- an estimate, the same one a careful human player makes."""

from functools import lru_cache
from itertools import product
from typing import List, Tuple

from traveler_quartet.rules.board import Board

DICE = {total: (6 - abs(total - 7)) / 36 for total in range(2, 13)}
ITERATIONS = 300


def landing_frequencies(board: Board) -> Tuple[float, ...]:
    """The share of moves that end on each square, in the long run."""
    return _frequencies(tuple(square.kind for square in board.squares))


def _step(frequencies: List[float], target: Tuple[int, ...]) -> List[float]:
    n = len(frequencies)
    following = [0.0] * n
    for square, total in product(range(n), DICE):
        following[target[(square + total) % n]] += frequencies[square] * DICE[total]
    return following


@lru_cache(maxsize=8)
def _frequencies(kinds: Tuple[str, ...]) -> Tuple[float, ...]:
    dungeon = kinds.index("dungeon")
    target = tuple(dungeon if kind == "go_to_dungeon" else i for i, kind in enumerate(kinds))
    frequencies = [1.0 / len(kinds)] * len(kinds)
    for _ in range(ITERATIONS):
        frequencies = _step(frequencies, target)
    return tuple(frequencies)
