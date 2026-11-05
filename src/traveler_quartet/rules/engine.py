from dataclasses import dataclass, replace
from typing import Optional, Tuple

from traveler_quartet.rules.board import Board, load_board
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.economy import Economy, Owners, load_economy, rent
from traveler_quartet.rules.movement import advance


class IllegalAction(ValueError):
    """The action is not among the legal actions of the pending question."""


@dataclass(frozen=True)
class Player:
    position: int
    cash: int


@dataclass(frozen=True)
class Event:
    kind: str
    player: int
    data: Tuple[Tuple[str, object], ...] = ()


@dataclass(frozen=True)
class GameState:
    board: Board
    economy: Economy
    seed: int
    players: Tuple[Player, ...]
    owners: Owners
    current: int = 0
    round: int = 1
    rolls: int = 0
    pending: str = "roll"

    @property
    def over(self) -> bool:
        return self.pending == "over"


Step = Tuple[GameState, Tuple[Event, ...]]

LEGAL = {"roll": ("roll",), "buy": ("buy", "pass"), "over": ()}


def new_game(seed: int, player_count: int,
             board: Optional[Board] = None, economy: Optional[Economy] = None) -> GameState:
    board = board or load_board()
    economy = economy or load_economy()
    players = tuple(Player(position=0, cash=economy.start_cash) for _ in range(player_count))
    return GameState(board=board, economy=economy, seed=seed, players=players,
                     owners=(None,) * len(board.squares))


def legal_actions(state: GameState) -> Tuple[str, ...]:
    return LEGAL[state.pending]


def apply(state: GameState, action: str) -> Step:
    if action not in legal_actions(state):
        raise IllegalAction(f"{action!r} is not legal now; legal: {legal_actions(state)}")
    handler = {"roll": _roll, "buy": _buy, "pass": _pass}[action]
    return handler(state)


def _with_player(state: GameState, index: int, player: Player) -> GameState:
    players = state.players[:index] + (player,) + state.players[index + 1:]
    return replace(state, players=players)


def _change_cash(state: GameState, index: int, amount: int) -> GameState:
    player = state.players[index]
    return _with_player(state, index, replace(player, cash=player.cash + amount))


def _end_turn(state: GameState) -> GameState:
    following = (state.current + 1) % len(state.players)
    next_round = state.round + 1 if following == 0 else state.round
    if next_round > state.economy.rounds:
        return replace(state, pending="over")
    return replace(state, current=following, round=next_round, pending="roll")


def _roll(state: GameState) -> Step:
    me = state.current
    dice = roll(state.seed, state.rolls)
    position, passed = advance(state.players[me].position, sum(dice), len(state.board.squares))
    state = replace(state, rolls=state.rolls + 1)
    state = _with_player(state, me, replace(state.players[me], position=position))
    events = [Event("rolled", me, (("dice", dice), ("square", position)))]
    if passed:
        state = _change_cash(state, me, state.economy.salary)
        events.append(Event("passed_start", me, (("salary", state.economy.salary),)))
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
    due = rent(state.board, state.economy, state.owners, index)
    state = _change_cash(_change_cash(state, me, -due), owner, due)
    return _end_turn(state), (Event("rent_paid", me, (("to", owner), ("amount", due))),)


def _buy(state: GameState) -> Step:
    me = state.current
    index = state.players[me].position
    price = state.board.squares[index].price
    owners = state.owners[:index] + (me,) + state.owners[index + 1:]
    state = _change_cash(replace(state, owners=owners), me, -price)
    return _end_turn(state), (Event("bought", me, (("square", index), ("price", price))),)


def _pass(state: GameState) -> Step:
    return _end_turn(state), (Event("declined", state.current, (("square", state.players[state.current].position),)),)
