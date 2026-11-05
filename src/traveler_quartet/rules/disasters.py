import random
from dataclasses import replace
from typing import Tuple

from traveler_quartet.rules.economy import STALL, owns_whole_town
from traveler_quartet.rules.state import GameState, change_cash, set_at

DAMAGE = {1: 1, 3: 2, 5: 3}


def damage(face: int) -> int:
    """Even: nothing; 1, 3, 5: one, two, three buildings (D19)."""
    return DAMAGE.get(face, 0)


def _lower_one(state: GameState, index: int) -> GameState:
    level = state.buildings[index]
    if level == STALL:
        back = state.economy.houses_before_stall if state.houses_left >= state.economy.houses_before_stall else 0
        state = replace(state, stalls_left=state.stalls_left + 1, houses_left=state.houses_left - back)
        return replace(state, buildings=set_at(state.buildings, index, back))
    return replace(state, buildings=set_at(state.buildings, index, level - 1), houses_left=state.houses_left + 1)


def destroy(state: GameState, town: str, count: int, target: str) -> Tuple[GameState, Tuple[int, ...]]:
    """Take down `count` buildings in a town: at random (a mindless disaster), or the most expensive first (an
    intelligent one). No compensation."""
    rng = random.Random(f"disaster:{state.seed}:{state.rolls}:{town}")
    hit = []
    for _ in range(count):
        built = [i for i in state.board.towns[town] if state.buildings[i] > 0]
        if not built:
            break
        index = rng.choice(built) if target == "random" else max(built, key=lambda i: (state.board.squares[i].price, i))
        state = _lower_one(state, index)
        hit.append(index)
    return state, tuple(hit)


def buildings_of(state: GameState, player: int, towns: Tuple[str, ...]) -> int:
    squares = [i for town in towns for i in state.board.towns[town]]
    return sum(1 for i in squares if state.owners[i] == player and state.buildings[i] > 0)


def owns_a_whole_pair(state: GameState, player: int, town: str) -> bool:
    pair = next((p for p in state.economy.pairs if town in p), ())
    return bool(pair) and all(owns_whole_town(state.board, state.owners, t, player) for t in pair)


def pay_what_he_can(state: GameState, player: int, amount: int) -> Tuple[GameState, int]:
    """Someone whose turn it is not pays what he can to the bank -- a debt only opens on one's own turn (D33)."""
    paid = min(amount, max(state.players[player].cash, 0))
    return change_cash(state, player, -paid), paid
