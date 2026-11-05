from dataclasses import replace

from traveler_quartet.rules import finance
from traveler_quartet.rules.card_effects import resolve
from traveler_quartet.rules.dungeon import send_to_dungeon
from traveler_quartet.rules.portals import can_jump
from traveler_quartet.rules.properties import is_property, property_rent
from traveler_quartet.rules.state import Event, GameState, Step, change_cash
from traveler_quartet.rules.turns import finish


def after_landing(state: GameState) -> GameState:
    """A portal offers its jump; otherwise the move is over."""
    return replace(state, pending="jump") if can_jump(state) else finish(state)


def _property(state: GameState, index: int) -> Step:
    me, owner = state.current, state.owners[index]
    if owner is None:
        affordable = state.players[me].cash >= state.board.squares[index].price
        return (replace(state, pending="buy"), ()) if affordable else (after_landing(state), ())
    if owner == me:
        return after_landing(state), ()
    due = property_rent(state, index, state.last_dice)
    state = finance.charge(state, due, owner)
    if state.pending == "debt":
        return state, (Event("debt_opened", me, (("to", owner), ("amount", due))),)
    return after_landing(state), (Event("rent_paid", me, (("to", owner), ("amount", due))),)


def _tax(state: GameState, index: int) -> Step:
    me, due = state.current, state.board.squares[index].amount
    state = finance.charge(state, due, None, to_jackpot=True)
    if state.pending == "debt":
        return state, (Event("debt_opened", me, (("to", "jackpot"), ("amount", due))),)
    return after_landing(state), (Event("tax_paid", me, (("amount", due),)),)


def _park(state: GameState, index: int) -> Step:
    me, won = state.current, state.jackpot
    state = change_cash(replace(state, jackpot=0), me, won)
    return after_landing(state), (Event("jackpot_won", me, (("amount", won),)),)


def land(state: GameState, index: int) -> Step:
    kind = state.board.squares[index].kind
    if is_property(state, index):
        return _property(state, index)
    if kind == "tax":
        return _tax(state, index)
    if kind == "park":
        return _park(state, index)
    if kind == "go_to_dungeon":
        return send_to_dungeon(state)
    if kind in ("chance", "event"):
        return _card(state, kind)
    return after_landing(state), ()


def _card(state: GameState, deck: str) -> Step:
    state, events, nxt = resolve(state, deck)
    if nxt == "land":
        state, more = land(state, state.players[state.current].position)
        return state, events + more
    return (after_landing(state) if nxt == "continue" else state), events
