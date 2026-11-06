"""The Adaptive computer (decision D42): the Hard computer, except that it buys, bids and builds by the NUMBERS of the
rules (`economics.py`) instead of thresholds written for today's rules -- so a change of rules changes its play.
Everything else (the danger on the board, the trades, the dungeon, the curses) is the Hard computer's."""

from typing import Optional, Tuple

from traveler_quartet.players.economics import buy_gain, house_gain, worth
from traveler_quartet.players.hard import FLOOR, _answer, _arg, _completes, _danger, _leader, _turn_start, hard
from traveler_quartet.rules.buildings import house_cost
from traveler_quartet.rules.engine import actor
from traveler_quartet.rules.state import GameState


def _buy(state: GameState) -> str:
    me = state.current
    square = state.players[me].position
    floor = FLOOR if _completes(state, (square,), me) else _danger(state, me)
    affordable = state.players[me].cash - state.board.squares[square].price >= floor
    return "buy" if affordable and buy_gain(state, square, me) >= 0 else "pass"


def _cap(state: GameState, square: int) -> float:
    me = actor(state)
    return min(worth(state, square, me), state.players[me].cash - _danger(state, me))


def _bid(state: GameState, legal: Tuple[str, ...]) -> str:
    a = state.auction
    return "raise:5" if "raise:5" in legal and a.price + 5 <= _cap(state, a.square) else "drop"


def _sealed(state: GameState, legal: Tuple[str, ...]) -> str:
    cap = _cap(state, state.sealed.square)
    return max((a for a in legal if _arg(a) <= max(cap, 0)), key=_arg)


def _paying_house(state: GameState, legal: Tuple[str, ...], cash: int, danger: int) -> Optional[str]:
    """The house that gains the most per gold before the end -- only if it gains at all."""
    builds = [a for a in legal if a.startswith("build:") and cash - house_cost(state, _arg(a)) >= danger]
    gains = [(house_gain(state, _arg(a)) / house_cost(state, _arg(a)), -_arg(a), a) for a in builds]
    best = max(gains, default=None)
    return best[2] if best and best[0] > 0 else None


def adaptive(state: GameState, legal: Tuple[str, ...]) -> str:
    if state.pending == "roll":
        return _turn_start(state, legal, choose_house=_paying_house)
    if state.pending == "buy":
        return _buy(state)
    if state.pending == "auction":
        return _bid(state, legal)
    if state.pending == "sealed":
        return _sealed(state, legal)
    if state.pending == "trade":
        return _answer(state)
    if state.pending == "target":
        return _leader(state, legal)
    return hard(state, legal)
