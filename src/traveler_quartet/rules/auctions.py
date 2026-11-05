"""The classic auction at a district's first sale (D31): from 0, raises of +5 / +10 / +25, one turn around the table per
raise; who drops out does not come back; the last one standing buys; nobody -> the district stays free."""

from dataclasses import dataclass, replace
from typing import Optional, Tuple

from traveler_quartet.rules.state import Event, GameState, change_cash, set_at

RAISES = (5, 10, 25)


@dataclass(frozen=True)
class Auction:
    square: int
    bidders: Tuple[int, ...]
    turn: int = 0
    price: int = 0
    leader: Optional[int] = None


def start(state: GameState, square: int) -> GameState:
    n = len(state.players)
    order = tuple((state.current + k) % n for k in range(n) if not state.players[(state.current + k) % n].out)
    return replace(state, pending="auction", auction=Auction(square=square, bidders=order))


def bidder(state: GameState) -> int:
    return state.auction.bidders[state.auction.turn]


def legal(state: GameState) -> Tuple[str, ...]:
    a, cash = state.auction, state.players[bidder(state)].cash
    return tuple(f"raise:{r}" for r in RAISES if a.price + r <= cash) + ("drop",)


def _finished(a: Auction) -> bool:
    return not a.bidders or (len(a.bidders) == 1 and a.leader == a.bidders[0])


def _close(state: GameState) -> Tuple[GameState, Tuple[Event, ...]]:
    a = state.auction
    state = replace(state, auction=None, pending="auction_closed")
    if a.leader is None:
        return state, (Event("auction_unsold", state.current, (("square", a.square),)),)
    state = change_cash(replace(state, owners=set_at(state.owners, a.square, a.leader)), a.leader, -a.price)
    return state, (Event("auction_won", a.leader, (("square", a.square), ("price", a.price), ("bank", -a.price))),)


def raise_bid(state: GameState, amount: int) -> Tuple[GameState, Tuple[Event, ...], bool]:
    a, who = state.auction, bidder(state)
    a = replace(a, price=a.price + amount, leader=who, turn=(a.turn + 1) % len(a.bidders))
    state = replace(state, auction=a)
    events = (Event("bid", who, (("square", a.square), ("price", a.price))),)
    if _finished(a):
        state, closed = _close(state)
        return state, events + closed, True
    return state, events, False


def drop(state: GameState) -> Tuple[GameState, Tuple[Event, ...], bool]:
    a, who = state.auction, bidder(state)
    bidders = a.bidders[:a.turn] + a.bidders[a.turn + 1:]
    turn = a.turn % len(bidders) if bidders else 0
    state = replace(state, auction=replace(a, bidders=bidders, turn=turn))
    events = (Event("dropped", who, (("square", a.square),)),)
    if _finished(state.auction):
        state, closed = _close(state)
        return state, events + closed, True
    return state, events, False


@dataclass(frozen=True)
class Sealed:
    """The bank's sealed-bid auction (D30): each player still in the game writes ONE secret bid; the highest wins
    (a tie goes to the first in the table order); no bid above 0 -> the district stays free."""
    queue: Tuple[int, ...]
    bidders: Tuple[int, ...]
    turn: int = 0
    bids: Tuple[int, ...] = ()

    @property
    def square(self) -> int:
        return self.queue[0]


SEALED_STEP = 5


def start_sealed(state: GameState, squares: Tuple[int, ...]) -> GameState:
    if not squares or state.over:
        return state
    n = len(state.players)
    order = tuple((state.current + k) % n for k in range(n) if not state.players[(state.current + k) % n].out)
    return replace(state, pending="sealed", sealed=Sealed(queue=tuple(squares), bidders=order))


def sealed_bidder(state: GameState) -> int:
    return state.sealed.bidders[state.sealed.turn]


def sealed_legal(state: GameState) -> Tuple[str, ...]:
    cash = state.players[sealed_bidder(state)].cash
    return tuple(f"bid:{amount}" for amount in range(0, cash + 1, SEALED_STEP))


def bid(state: GameState, amount: int) -> Tuple[GameState, Tuple[Event, ...]]:
    s = state.sealed
    s = replace(s, bids=s.bids + (amount,), turn=s.turn + 1)
    if s.turn < len(s.bidders):
        return replace(state, sealed=s), ()
    best = max(s.bids)
    events: Tuple[Event, ...] = ()
    if best > 0:
        winner = s.bidders[s.bids.index(best)]
        state = change_cash(replace(state, owners=set_at(state.owners, s.square, winner)), winner, -best)
        events = (Event("sealed_won", winner, (("square", s.square), ("price", best), ("bank", -best))),)
    rest = s.queue[1:]
    if rest:
        return replace(state, sealed=replace(s, queue=rest, turn=0, bids=())), events
    return replace(state, sealed=None, pending="roll"), events
