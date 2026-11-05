from dataclasses import replace
from typing import Callable, Dict, Optional, Tuple

from traveler_quartet.rules import auctions, buildings, dungeon, finance, partners, portals, trades
from traveler_quartet.rules.card_effects import crisis_on, resolve
from traveler_quartet.rules.cards import load_cards, shuffled_decks
from traveler_quartet.rules.board import Board, load_board
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.economy import Economy, load_economy
from traveler_quartet.rules.income import start_income
from traveler_quartet.rules.landing import after_landing, land
from traveler_quartet.rules.movement import advance
from traveler_quartet.rules.state import Event, GameState, Player, Step, change_cash, set_at, update_player
from traveler_quartet.rules.turns import end_turn

__all__ = ["Event", "GameState", "IllegalAction", "Player", "actor", "apply", "legal_actions", "negotiations", "new_game"]


class IllegalAction(ValueError):
    """The action is not among the legal actions of the pending question."""


def new_game(seed: int, player_count: int,
             board: Optional[Board] = None, economy: Optional[Economy] = None) -> GameState:
    board = board or load_board()
    economy = economy or load_economy()
    size = len(board.squares)
    players = tuple(Player(position=0, cash=economy.start_cash) for _ in range(player_count))
    catalog = load_cards()
    return GameState(board=board, economy=economy, seed=seed, players=players,
                     owners=(None,) * size, buildings=(0,) * size, mortgaged=(False,) * size,
                     houses_left=economy.houses_stock, stalls_left=economy.stalls_stock,
                     catalog=catalog, decks=shuffled_decks(catalog, seed), partners=(None,) * size)


def _square_actions(state: GameState, name: str, allowed: Callable[[GameState, int, int], bool]) -> Tuple[str, ...]:
    me = state.current
    return tuple(f"{name}:{i}" for i in range(len(state.board.squares)) if allowed(state, me, i))


def _raising_actions(state: GameState) -> Tuple[str, ...]:
    return _square_actions(state, "sell", buildings.can_sell) + _square_actions(state, "mortgage", finance.can_mortgage)


def actor(state: GameState) -> int:
    """Who must answer the pending question -- not always the player whose turn it is (architecture §3)."""
    if state.pending == "auction":
        return auctions.bidder(state)
    if state.pending == "trade":
        return state.trade.responder
    if state.pending == "stall_request":
        return state.owners[state.stall_request[1]]
    if state.pending == "sealed":
        return auctions.sealed_bidder(state)
    return state.current


def negotiations(state: GameState) -> Tuple[str, ...]:
    """The PARAMETERIZED actions open right now -- templates, not actions to play as they are: `offer:<player>` (then
    the six fields of the contract) and `counter` (the six fields). Kept apart from `legal_actions` on purpose: a
    template played bare is refused (E13)."""
    if state.pending == "roll":
        return _offer_actions(state)
    if state.pending == "trade" and state.trade.counters < trades.MAX_COUNTERS:
        return ("counter",)
    return ()


def _offer_actions(state: GameState) -> Tuple[str, ...]:
    if state.offers >= trades.MAX_OFFERS_PER_TURN:
        return ()
    return tuple(f"offer:{p}" for p in range(len(state.players)) if p != state.current and not state.players[p].out)


def _trade_terms(state: GameState, action: str):
    """A full offer or counter-offer, parsed and checked; None if it is not a legal contract right now."""
    name, _, rest = action.partition(":")
    fields = rest.split(":")
    if name == "offer" and len(fields) == 7 and f"offer:{fields[0]}" in negotiations(state):
        receiver, terms = int(fields[0]), trades.parse_terms(fields[1:])
        ok = terms is not None and trades.valid(state, state.current, receiver, terms)
        return (receiver, terms) if ok else None
    if name == "counter" and len(fields) == 6 and "counter" in negotiations(state):
        terms, t = trades.parse_terms(fields), state.trade
        ok = terms is not None and trades.valid(state, t.responder, t.proposer, terms)
        return (t.proposer, terms) if ok else None
    return None


def _dungeon_actions(state: GameState) -> Tuple[str, ...]:
    out = ("pay_exit",) if dungeon.can_pay_exit(state) else ()
    rope = dungeon.in_dungeon(state) and "rope" in state.players[state.current].cards
    return out + (("use_rope",) if rope else ())


def _curse_actions(state: GameState, held: bool) -> Tuple[str, ...]:
    if held and "curse" not in state.players[state.current].cards:
        return ()
    return tuple(f"curse:{p}" for p in range(len(state.players)) if p != state.current and not state.players[p].out)


def legal_actions(state: GameState) -> Tuple[str, ...]:
    if state.pending == "roll":
        return (("roll",) + _dungeon_actions(state) + _curse_actions(state, held=True)
                + _square_actions(state, "build", buildings.can_build) + _square_actions(state, "share_stall", partners.can_share)
                + _raising_actions(state)
                + _square_actions(state, "unmortgage", finance.can_unmortgage))
    if state.pending == "target":
        return _curse_actions(state, held=False)
    if state.pending == "auction":
        return auctions.legal(state)
    if state.pending == "trade":
        return ("accept", "refuse")
    if state.pending == "stall_request":
        return (("accept",) if partners.owner_can_pay(state) else ()) + ("refuse",)
    if state.pending == "sealed":
        return auctions.sealed_legal(state)
    if state.pending == "buy":
        return ("buy", "pass")
    if state.pending == "jump":
        return ("jump", "stay")
    if state.pending == "debt":
        return _raising_actions(state) or ("bankrupt",)
    return ()


def apply(state: GameState, action: str) -> Step:
    name, _, argument = action.partition(":")
    if name in ("offer", "counter"):
        contract = _trade_terms(state, action)
        if contract is None:
            raise IllegalAction(f"{action!r} is not a legal contract now")
        receiver, terms = contract
        return trades.offer(state, receiver, terms) if name == "offer" else trades.counter(state, terms)
    if action not in legal_actions(state):
        raise IllegalAction(f"{action!r} is not legal now; legal: {legal_actions(state)}")
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
    me, events = state.current, ()
    if dungeon.in_dungeon(state):
        state, events, nxt = resolve(state, "adventurer")
        if nxt == "done":
            return state, events
    dice = roll(state.seed, state.rolls)
    double = dice[0] == dice[1]
    state = replace(state, rolls=state.rolls + 1, last_dice=dice)
    events += (Event("rolled", me, (("dice", dice),)),)
    if dungeon.in_dungeon(state):
        if not double or state.players[me].dungeon_locked:
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
    square = state.players[state.current].position
    return auctions.start(state, square), (Event("declined", state.current, (("square", square),)),)


def _auction_step(state: GameState, step) -> Step:
    state, events, done = step
    return (after_landing(state) if done else state), events


def _drop(state: GameState) -> Step:
    return _auction_step(state, auctions.drop(state))


def _raise(state: GameState, amount: int) -> Step:
    return _auction_step(state, auctions.raise_bid(state, amount))


def _bankrupt(state: GameState) -> Step:
    freed = tuple(i for i, owner in enumerate(state.owners) if owner == state.current)
    state, events = finance.bankrupt(state)
    return auctions.start_sealed(end_turn(state), freed), events


def _curse(state: GameState, target: int) -> Step:
    me, per_building = state.current, state.catalog["curse"]["amount"]
    towns = tuple(state.board.towns)
    events = (Event("cursed", me, (("target", target),)),)
    if "mirror" in state.players[target].cards:
        state = update_player(state, target, cards=_without(state.players[target].cards, "mirror"))
        events += (Event("mirrored", target, (("back_to", me),)),)
        target = me
    state, event = crisis_on(state, target, towns, per_building)
    events += (event,)
    if state.pending == "target":
        return after_landing(state), events
    return update_player(state, me, cards=_without(state.players[me].cards, "curse")), events


def _without(cards: Tuple[str, ...], card: str) -> Tuple[str, ...]:
    out = list(cards)
    out.remove(card)
    return tuple(out)


SIMPLE_ACTIONS: Dict[str, Callable[[GameState], Step]] = {
    "roll": _roll, "buy": _buy, "pass": _pass, "bankrupt": _bankrupt,
    "jump": portals.jump, "stay": portals.stay, "pay_exit": dungeon.pay_exit, "use_rope": dungeon.use_rope, "drop": _drop,
    "accept": lambda s: (partners.accept if s.pending == "stall_request" else trades.accept)(s),
    "refuse": lambda s: (partners.refuse if s.pending == "stall_request" else trades.refuse)(s),
}
SQUARE_ACTIONS: Dict[str, Callable[[GameState, int], Step]] = {
    "build": buildings.build, "sell": buildings.sell,
    "mortgage": finance.mortgage, "unmortgage": finance.unmortgage, "curse": _curse, "raise": _raise, "share_stall": partners.request, "bid": auctions.bid,
}
