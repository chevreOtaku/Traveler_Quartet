import random
from typing import Optional, Tuple

from traveler_quartet.rules.buildings import house_cost
from traveler_quartet.rules.engine import actor, negotiations
from traveler_quartet.rules.state import GameState
from traveler_quartet.rules.trades import value_of

RESERVE = 100
TRADE_PREMIUM_PERCENT = 150
ACCEPT_GAIN_PERCENT = 120


def _rng(state: GameState, tag: str) -> random.Random:
    me = state.players[actor(state)]
    return random.Random(f"{tag}:{state.seed}:{state.rolls}:{actor(state)}:{me.cash}:{state.houses_left}:{state.pending}")


def _square(action: str) -> int:
    return int(action.split(":")[1])


def easy(state: GameState, legal: Tuple[str, ...]) -> str:
    """A credible beginner (avant-etape-6 §2): buys whenever it can pay, builds now and then, bids up to half the price,
    never trades nor shares a stall, never pays to leave the dungeon."""
    rng = _rng(state, "easy")
    me = actor(state)
    if state.pending == "buy":
        return "buy"
    if state.pending == "roll":
        builds = [a for a in legal if a.startswith("build:")]
        return rng.choice(builds) if builds and rng.random() < 0.3 else "roll"
    if state.pending == "auction":
        cap = state.board.squares[state.auction.square].price // 2
        return "raise:5" if "raise:5" in legal and state.auction.price + 5 <= cap else "drop"
    if state.pending == "sealed":
        cap = state.board.squares[state.sealed.square].price // 2
        return max((a for a in legal if int(a.split(":")[1]) <= cap), key=lambda a: int(a.split(":")[1]))
    if state.pending in ("trade", "stall_request"):
        return "refuse"
    if state.pending == "jump":
        return rng.choice(legal)
    if state.pending == "target":
        return rng.choice(legal)
    sells = [a for a in legal if a.startswith("sell:")]
    return (sells or [a for a in legal if a.startswith("mortgage:")] or list(legal))[0]


def _completing_offer(state: GameState, legal: Tuple[str, ...]) -> Optional[str]:
    """Buy the last districts of a town from its one other owner, at 1.5 times their price, keeping the reserve."""
    me, cash = state.current, state.players[state.current].cash
    for town, squares in state.board.towns.items():
        missing = [i for i in squares if state.owners[i] != me]
        others = {state.owners[i] for i in missing}
        if not missing or len(missing) == len(squares) or len(others) != 1 or None in others:
            continue
        rival = others.pop()
        if f"offer:{rival}" not in negotiations(state) or any(state.buildings[i] for i in squares):
            continue
        gold = value_of(state, 0, tuple(missing), ()) * TRADE_PREMIUM_PERCENT // 100
        if cash - gold >= RESERVE:
            return f"offer:{rival}:{gold}:::0:{','.join(map(str, missing))}:"
    return None


def _answer_offer(state: GameState) -> str:
    t = state.trade.terms
    given = value_of(state, t.ask_gold, t.ask_squares, t.ask_cards)
    received = value_of(state, t.give_gold, t.give_squares, t.give_cards)
    return "accept" if received * 100 >= given * ACCEPT_GAIN_PERCENT else "refuse"


def _turn_start(state: GameState, legal: Tuple[str, ...], cash: int) -> str:
    if "use_rope" in legal:
        return "use_rope"
    curses = [a for a in legal if a.startswith("curse:")]
    if curses:
        return max(curses, key=lambda a: (state.players[_square(a)].cash, -_square(a)))
    affordable = [a for a in legal if a.startswith("build:") and cash - house_cost(state, _square(a)) >= RESERVE]
    if affordable:
        return affordable[0]
    shares = [a for a in legal if a.startswith("share_stall:") and cash - house_cost(state, _square(a)) // 2 >= RESERVE]
    if shares:
        return shares[0]
    offer = _completing_offer(state, legal) if state.offers == 0 else None
    return offer or "roll"


def normal(state: GameState, legal: Tuple[str, ...]) -> str:
    """Simple rules: keep a reserve of 100; buy, build and bid up to the price while it holds; buy the last districts
    of a town; accept a trade worth 20 % more than it costs; sell houses before mortgaging."""
    me = actor(state)
    cash = state.players[me].cash
    if state.pending == "target":
        return max(legal, key=lambda a: (state.players[_square(a)].cash, -_square(a)))
    if state.pending == "buy":
        price = state.board.squares[state.players[me].position].price
        return "buy" if cash - price >= RESERVE else "pass"
    if state.pending == "auction":
        a = state.auction
        cap = min(state.board.squares[a.square].price, cash - RESERVE)
        return "raise:5" if "raise:5" in legal and a.price + 5 <= cap else "drop"
    if state.pending == "sealed":
        cap = min(state.board.squares[state.sealed.square].price, cash - RESERVE)
        return max((a for a in legal if int(a.split(":")[1]) <= max(cap, 0)), key=lambda a: int(a.split(":")[1]))
    if state.pending == "trade":
        return _answer_offer(state)
    if state.pending == "stall_request":
        return "accept" if "accept" in legal else "refuse"
    if state.pending == "jump":
        return "jump"
    if state.pending == "roll":
        return _turn_start(state, legal, cash)
    sells = [a for a in legal if a.startswith("sell:")]
    return (sells or [a for a in legal if a.startswith("mortgage:")] or list(legal))[0]


BOTS = {"easy": easy, "normal": normal}
