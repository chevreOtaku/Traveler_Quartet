import random
from typing import Tuple

from traveler_quartet.rules.buildings import house_cost
from traveler_quartet.rules.state import GameState

RESERVE = 100


def _rng(state: GameState, tag: str) -> random.Random:
    me = state.players[state.current]
    return random.Random(f"{tag}:{state.seed}:{state.rolls}:{state.current}:{me.cash}:{state.houses_left}")


def _square(action: str) -> int:
    return int(action.partition(":")[2])


def easy(state: GameState, legal: Tuple[str, ...]) -> str:
    """Plays at random: buys half the time, sometimes builds, never raises money unless it must."""
    rng = _rng(state, "easy")
    if state.pending == "buy":
        return rng.choice(("buy", "pass"))
    if state.pending == "roll":
        builds = [a for a in legal if a.startswith("build:")]
        return rng.choice(builds) if builds and rng.random() < 0.2 else "roll"
    return rng.choice(legal)


def normal(state: GameState, legal: Tuple[str, ...]) -> str:
    """Simple rules: keep a reserve of 100, buy and build while it holds, sell houses before mortgaging."""
    cash = state.players[state.current].cash
    curses = [a for a in legal if a.startswith("curse:")]
    if curses:
        return max(curses, key=lambda a: (state.players[_square(a)].cash, -_square(a)))
    if "use_rope" in legal:
        return "use_rope"
    if state.pending == "buy":
        price = state.board.squares[state.players[state.current].position].price
        return "buy" if cash - price >= RESERVE else "pass"
    if state.pending == "roll":
        affordable = [a for a in legal if a.startswith("build:") and cash - house_cost(state, _square(a)) >= RESERVE]
        return affordable[0] if affordable else "roll"
    sells = [a for a in legal if a.startswith("sell:")]
    return (sells or [a for a in legal if a.startswith("mortgage:")] or list(legal))[0]


BOTS = {"easy": easy, "normal": normal}
