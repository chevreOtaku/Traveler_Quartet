"""The Hard computer (D39): it CALCULATES. Where pawns land (`landing`), what completes its town or a rival's, what a
house earns per gold spent, who leads in net worth. Its reserve is the DANGER on the board -- the highest rent a rival
can charge right now -- not a fixed amount."""

from typing import Optional, Tuple

from traveler_quartet.players.bots import normal
from traveler_quartet.players.landing import landing_frequencies
from traveler_quartet.rules.buildings import house_cost
from traveler_quartet.rules.economy import rent
from traveler_quartet.rules.endgame import net_worth
from traveler_quartet.rules.engine import actor, negotiations
from traveler_quartet.rules.finance import unmortgage_cost
from traveler_quartet.rules.state import GameState, set_at
from traveler_quartet.rules.trades import value_of

FLOOR = 25
COMPLETE_BID_PERCENT, BLOCK_BID_PERCENT = 150, 130
ACCEPT_GAIN_PERCENT, COMPLETION_PRICE_PERCENT = 110, 200
OFFER_PREMIUMS = (130, 170, 200)
LATE_ROUND_PERCENT = 60


def _arg(action: str) -> int:
    return int(action.split(":")[1])


def _danger(state: GameState, me: int) -> int:
    rents = (rent(state.board, state.economy, state.owners, i, state.buildings, state.mortgaged)
             for i, owner in enumerate(state.owners) if owner not in (None, me))
    return max(FLOOR, max(rents, default=0))


def _town(state: GameState, square: int) -> Tuple[int, ...]:
    town = state.board.squares[square].town
    return state.board.towns[town] if town else ()


def _completes(state: GameState, squares: Tuple[int, ...], player: int) -> bool:
    """After receiving `squares`, does `player` own a whole town that it did not own before?"""
    return any(all(state.owners[i] == player or i in squares for i in _town(state, s)) for s in squares if _town(state, s))


def _blocks(state: GameState, square: int, me: int) -> bool:
    rivals = {state.owners[i] for i in _town(state, square) if i != square}
    return len(rivals) == 1 and None not in rivals and me not in rivals


def _worth(state: GameState, square: int, me: int) -> int:
    price = state.board.squares[square].price
    if _completes(state, (square,), me):
        return price * COMPLETE_BID_PERCENT // 100
    return price * BLOCK_BID_PERCENT // 100 if _blocks(state, square, me) else price


def _bid(state: GameState, legal: Tuple[str, ...], square: int, price: int) -> str:
    me = actor(state)
    cap = min(_worth(state, square, me), state.players[me].cash - _danger(state, me))
    return "raise:5" if "raise:5" in legal and price + 5 <= cap else "drop"


def _sealed(state: GameState, legal: Tuple[str, ...]) -> str:
    me = actor(state)
    cap = min(_worth(state, state.sealed.square, me), state.players[me].cash - _danger(state, me))
    return max((a for a in legal if _arg(a) <= max(cap, 0)), key=_arg)


def _buy(state: GameState) -> str:
    me = state.current
    square = state.players[me].position
    floor = FLOOR if _completes(state, (square,), me) else _danger(state, me)
    return "buy" if state.players[me].cash - state.board.squares[square].price >= floor else "pass"


def _answer(state: GameState) -> str:
    t, proposer = state.trade.terms, state.trade.proposer
    given = value_of(state, t.ask_gold, t.ask_squares, t.ask_cards)
    received = value_of(state, t.give_gold, t.give_squares, t.give_cards)
    needed = COMPLETION_PRICE_PERCENT if _completes(state, t.ask_squares, proposer) else ACCEPT_GAIN_PERCENT
    return "accept" if received * 100 >= given * needed else "refuse"


def _leader(state: GameState, legal: Tuple[str, ...]) -> str:
    return max(legal, key=lambda a: (net_worth(state, _arg(a)), -_arg(a)))


def _house_return(state: GameState, square: int) -> float:
    now = rent(state.board, state.economy, state.owners, square, state.buildings, state.mortgaged)
    higher = set_at(state.buildings, square, state.buildings[square] + 1)
    after = rent(state.board, state.economy, state.owners, square, higher, state.mortgaged)
    return landing_frequencies(state.board)[square] * (after - now) / house_cost(state, square)


def _dungeon_move(state: GameState, legal: Tuple[str, ...]) -> Optional[str]:
    late = state.round * 100 > state.economy.rounds * LATE_ROUND_PERCENT
    free = any(owner is None and s.kind == "district" for owner, s in zip(state.owners, state.board.squares))
    if late or not free:
        return None
    return next((a for a in ("use_rope", "pay_exit") if a in legal), None)


def _completing_offer(state: GameState) -> Optional[str]:
    me, cash = state.current, state.players[state.current].cash
    premium = OFFER_PREMIUMS[min(state.offers, len(OFFER_PREMIUMS) - 1)]
    for squares in state.board.towns.values():
        missing = tuple(i for i in squares if state.owners[i] != me)
        rivals = {state.owners[i] for i in missing}
        if not missing or len(missing) == len(squares) or len(rivals) != 1 or None in rivals:
            continue
        rival = rivals.pop()
        if f"offer:{rival}" not in negotiations(state) or any(state.buildings[i] for i in squares):
            continue
        gold = value_of(state, 0, missing, ()) * premium // 100
        if cash - gold >= _danger(state, me):
            return f"offer:{rival}:{gold}:::0:{','.join(map(str, missing))}:"
    return None


def _best_house(state: GameState, legal: Tuple[str, ...], cash: int, danger: int) -> Optional[str]:
    """The Hard choice: the house that earns the most rent per gold, if the danger on the board allows it."""
    builds = [a for a in legal if a.startswith("build:") and cash - house_cost(state, _arg(a)) >= danger]
    return max(builds, key=lambda a: (_house_return(state, _arg(a)), -_arg(a))) if builds else None


def _turn_start(state: GameState, legal: Tuple[str, ...], choose_house=_best_house) -> str:
    me = state.current
    cash, danger = state.players[me].cash, _danger(state, me)
    leave = _dungeon_move(state, legal)
    if leave:
        return leave
    curses = [a for a in legal if a.startswith("curse:")]
    if curses:
        return _leader(state, curses)
    house = choose_house(state, legal, cash, danger)
    if house:
        return house
    lifts = [a for a in legal if a.startswith("unmortgage:") and cash - unmortgage_cost(state, _arg(a)) >= 2 * danger]
    if lifts:
        return lifts[0]
    shares = [a for a in legal if a.startswith("share_stall:") and cash - house_cost(state, _arg(a)) // 2 >= danger]
    if shares:
        return shares[0]
    return _completing_offer(state) or "roll"


def hard(state: GameState, legal: Tuple[str, ...]) -> str:
    if state.pending == "roll":
        return _turn_start(state, legal)
    if state.pending == "buy":
        return _buy(state)
    if state.pending == "auction":
        return _bid(state, legal, state.auction.square, state.auction.price)
    if state.pending == "sealed":
        return _sealed(state, legal)
    if state.pending == "trade":
        return _answer(state)
    if state.pending == "target":
        return _leader(state, legal)
    return normal(state, legal)
