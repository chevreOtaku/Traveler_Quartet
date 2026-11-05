from typing import Tuple


def advance(position: int, steps: int, board_size: int) -> Tuple[int, bool]:
    """The new position, and whether the move went past Start."""
    target = position + steps
    return target % board_size, target >= board_size
