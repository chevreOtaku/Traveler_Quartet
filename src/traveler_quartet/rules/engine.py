from dataclasses import replace
from typing import Callable, Dict, Optional, Tuple

from traveler_quartet.rules import buildings, dungeon, finance, portals
from traveler_quartet.rules.board import Board, load_board
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.economy import Economy, load_economy
from traveler_quartet.rules.income import start_income
from traveler_quartet.rules.landing import after_landing, land
from traveler_quartet.rules.movement import advance
from traveler_quartet.rules.state import Event, GameState, Player, Step, change_cash, set_at, update_player
from traveler_quartet.rules.turns import end_turn

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
        exit_ = ("pay_exit",) if dungeon.can_pay_exit(state) else ()
        return (("roll",) + exit_ + _square_actions(state, "build", buildings.can_build) + _raising_actions(state)
                + _square_actions(state, "unmortgage", finance.can_unmortgage))
    if state.pending == "buy":
        return ("buy", "pass")
    if state.pending == "jump":
        return ("jump", "stay")
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
    return end_turn(state), events + paid


def _roll(state: GameState) -> Step:
    me = state.current
    dice = roll(state.seed, state.rolls)
    double = dice[0] == dice[1]
    state = replace(state, rolls=state.rolls + 1, last_dice=dice)
    events = (Event("rolled", me, (("dice", dice),)),)
    if dungeon.in_dungeon(state):
        if not double:
            state, inside = dungeon.stay_inside(state)
            return state, events + inside
        state = update_player(state, me, dungeon_turns=0)
        events += (Event("left_dungeon", me, (("by", "double"),)),)
    else:
        doubles = state.doubles + 1 if double else 0
        if doubles >= state.economy.doubles_to_dungeon:
            state, sent = dungeon.send_to_dungeon(state)
            return state, events + sent
        state = replace(state, doubles=doubles)
    return _move(state, sum(dice), events)


def _move(state: GameState, steps: int, events: Tuple[Event, ...]) -> Step:
    me = state.current
    position, passed = advance(state.players[me].position, steps, len(state.board.squares))
    state = update_player(state, me, position=position)
    if passed:
        income = start_income(state, me)
        state = update_player(change_cash(state, me, income), me, jump_ready=True)
        events += (Event("passed_start", me, (("amount", income), ("bank", income))),)
    state, landed = land(state, position)
    return state, events + landed


def _buy(state: GameState) -> Step:
    me = state.current
    index = state.players[me].position
    price = state.board.squares[index].price
    state = change_cash(replace(state, owners=set_at(state.owners, index, me)), me, -price)
    return after_landing(state), (Event("bought", me, (("square", index), ("price", price), ("bank", -price))),)


def _pass(state: GameState) -> Step:
    return after_landing(state), (Event("declined", state.current, (("square", state.players[state.current].position),)),)


def _bankrupt(state: GameState) -> Step:
    state, events = finance.bankrupt(state)
    return end_turn(state), events


SIMPLE_ACTIONS: Dict[str, Callable[[GameState], Step]] = {
    "roll": _roll, "buy": _buy, "pass": _pass, "bankrupt": _bankrupt,
    "jump": portals.jump, "stay": portals.stay, "pay_exit": dungeon.pay_exit,
}
SQUARE_ACTIONS: Dict[str, Callable[[GameState, int], Step]] = {
    "build": buildings.build, "sell": buildings.sell,
    "mortgage": finance.mortgage, "unmortgage": finance.unmortgage,
}
