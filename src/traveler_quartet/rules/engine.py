from dataclasses import replace
from typing import Callable, Dict, Optional, Tuple

from traveler_quartet.rules import buildings, finance
from traveler_quartet.rules.board import Board, load_board
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.economy import Economy, load_economy, rent
from traveler_quartet.rules.income import start_income
from traveler_quartet.rules.movement import advance
from traveler_quartet.rules.state import Event, GameState, Player, Step, change_cash, set_at, with_player

__all__ = ["Event", "GameState", "IllegalAction", "Player", "apply", "legal_actions", "new_game"]


class IllegalAction(ValueError):
    """The action is not among the legal actions of the pending question."""


def new_game(seed: int, player_count: int,
             board: Optional[Board] = None, economy: Optional[Economy] = None) -> GameState:
    board = board or load_board()
    economy = economy or load_economy()
    size = len(board.squares)
    players = tuple(Player(position=0, cash=economy.start_cash) for _ in range(player_count))
    return GameState(board=board, economy=economy, seed=seed, players=players,
                     owners=(None,) * size, buildings=(0,) * size, mortgaged=(False,) * size,
                     houses_left=economy.houses_stock, stalls_left=economy.stalls_stock)


def _square_actions(state: GameState, name: str, allowed: Callable[[GameState, int, int], bool]) -> Tuple[str, ...]:
    me = state.current
    return tuple(f"{name}:{i}" for i in range(len(state.board.squares)) if allowed(state, me, i))


def _raising_actions(state: GameState) -> Tuple[str, ...]:
    return _square_actions(state, "sell", buildings.can_sell) + _square_actions(state, "mortgage", finance.can_mortgage)


def legal_actions(state: GameState) -> Tuple[str, ...]:
    if state.pending == "roll":
        return (("roll",) + _square_actions(state, "build", buildings.can_build) + _raising_actions(state)
                + _square_actions(state, "unmortgage", finance.can_unmortgage))
    if state.pending == "buy":
        return ("buy", "pass")
    if state.pending == "debt":
        return _raising_actions(state) or ("bankrupt",)
    return ()


def apply(state: GameState, action: str) -> Step:
    if action not in legal_actions(state):
        raise IllegalAction(f"{action!r} is not legal now; legal: {legal_actions(state)}")
    name, _, argument = action.partition(":")
    if argument:
        state, events = SQUARE_ACTIONS[name](state, int(argument))
        return _after_raising(state, events)
    return SIMPLE_ACTIONS[name](state)


def _after_raising(state: GameState, events: Tuple[Event, ...]) -> Step:
    if state.pending != "debt" or not finance.can_settle(state):
        return state, events
    state, paid = finance.settle(state)
    return _end_turn(state), events + paid


def _active(state: GameState) -> int:
    return sum(1 for p in state.players if not p.out)


def _end_turn(state: GameState) -> GameState:
    if _active(state) <= 1:
        return replace(state, pending="over")
    following, next_round = state.current, state.round
    while True:
        following = (following + 1) % len(state.players)
        next_round += following == 0
        if not state.players[following].out:
            break
    if next_round > state.economy.rounds:
        return replace(state, pending="over")
    return replace(state, current=following, round=next_round, pending="roll")


def _roll(state: GameState) -> Step:
    me = state.current
    dice = roll(state.seed, state.rolls)
    position, passed = advance(state.players[me].position, sum(dice), len(state.board.squares))
    state = replace(state, rolls=state.rolls + 1)
    state = with_player(state, me, replace(state.players[me], position=position))
    events = [Event("rolled", me, (("dice", dice), ("square", position)))]
    if passed:
        income = start_income(state, me)
        state = change_cash(state, me, income)
        events.append(Event("passed_start", me, (("amount", income), ("bank", income))))
    state, landed = _land(state, position)
    return state, tuple(events) + landed


def _land(state: GameState, index: int) -> Step:
    me = state.current
    square = state.board.squares[index]
    owner = state.owners[index]
    if square.kind != "district" or owner == me:
        return _end_turn(state), ()
    if owner is None:
        affordable = state.players[me].cash >= square.price
        return (replace(state, pending="buy"), ()) if affordable else (_end_turn(state), ())
    due = rent(state.board, state.economy, state.owners, index, state.buildings, state.mortgaged)
    state = finance.charge(state, due, owner)
    if state.pending == "debt":
        return state, (Event("debt_opened", me, (("to", owner), ("amount", due))),)
    return _end_turn(state), (Event("rent_paid", me, (("to", owner), ("amount", due))),)


def _buy(state: GameState) -> Step:
    me = state.current
    index = state.players[me].position
    price = state.board.squares[index].price
    state = change_cash(replace(state, owners=set_at(state.owners, index, me)), me, -price)
    return _end_turn(state), (Event("bought", me, (("square", index), ("price", price), ("bank", -price))),)


def _pass(state: GameState) -> Step:
    return _end_turn(state), (Event("declined", state.current, (("square", state.players[state.current].position),)),)


def _bankrupt(state: GameState) -> Step:
    state, events = finance.bankrupt(state)
    return _end_turn(state), events


SIMPLE_ACTIONS: Dict[str, Callable[[GameState], Step]] = {
    "roll": _roll, "buy": _buy, "pass": _pass, "bankrupt": _bankrupt,
}
SQUARE_ACTIONS: Dict[str, Callable[[GameState, int], Step]] = {
    "build": buildings.build, "sell": buildings.sell,
    "mortgage": finance.mortgage, "unmortgage": finance.unmortgage,
}
