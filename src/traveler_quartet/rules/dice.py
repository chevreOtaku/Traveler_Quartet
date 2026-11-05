import random
from typing import Tuple


def roll(seed: int, number: int) -> Tuple[int, int]:
    """The two dice of roll number `number` in the game of seed `seed`: always the same pair."""
    rng = random.Random(f"{seed}:{number}")
    return rng.randint(1, 6), rng.randint(1, 6)
