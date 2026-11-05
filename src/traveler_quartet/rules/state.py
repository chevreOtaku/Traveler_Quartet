from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

from traveler_quartet.rules.board import Board
from traveler_quartet.rules.economy import Economy, Owners


@dataclass(frozen=True)
class Player:
    position: int
    cash: int
    out: bool = False
    jump_ready: bool = True
    dungeon_turns: int = 0
    dungeon_locked: bool = False
    cards: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Event:
    kind: str
    player: int
    data: Tuple[Tuple[str, object], ...] = ()


@dataclass(frozen=True)
class Debt:
    amount: int
    creditor: Optional[int]
    to_jackpot: bool = False


@dataclass(frozen=True)
class GameState:
    board: Board
    economy: Economy
    seed: int
    players: Tuple[Player, ...]
    owners: Owners
    buildings: Tuple[int, ...]
    mortgaged: Tuple[bool, ...]
    houses_left: int
    stalls_left: int
    current: int = 0
    round: int = 1
    rolls: int = 0
    pending: str = "roll"
    debt: Optional[Debt] = None
    jackpot: int = 0
    doubles: int = 0
    last_dice: Tuple[int, int] = (0, 0)
    catalog: Mapping[str, Mapping[str, object]] = field(default_factory=lambda: MappingProxyType({}))
    decks: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()
    discovered: Tuple[str, ...] = ()
    auction: Optional[object] = None
    trade: Optional[object] = None
    offers: int = 0
    partners: Tuple[Optional[int], ...] = ()
    stall_request: Optional[Tuple[int, int]] = None
    sealed: Optional[object] = None

    @property
    def over(self) -> bool:
        return self.pending == "over"


Step = Tuple[GameState, Tuple[Event, ...]]


def with_player(state: GameState, index: int, player: Player) -> GameState:
    return replace(state, players=state.players[:index] + (player,) + state.players[index + 1:])


def change_cash(state: GameState, index: int, amount: int) -> GameState:
    player = state.players[index]
    return with_player(state, index, replace(player, cash=player.cash + amount))


def set_at(table: tuple, index: int, value) -> tuple:
    return table[:index] + (value,) + table[index + 1:]


def update_player(state: GameState, index: int, **changes) -> GameState:
    return with_player(state, index, replace(state.players[index], **changes))
