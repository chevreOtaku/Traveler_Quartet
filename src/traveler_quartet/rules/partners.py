"""Shared stalls (D20): a rival builds a stall on a district of a town ready for one, WITH the owner's agreement; each
pays half; each earns +10 at Start; one partner per pair; selling it refunds the partner first (like a guarantor)."""

from dataclasses import replace
from typing import Optional, Tuple

from traveler_quartet.rules.buildings import house_cost
from traveler_quartet.rules.economy import STALL, owns_whole_town
from traveler_quartet.rules.state import Event, GameState, change_cash, set_at
from traveler_quartet.rules.trades import MAX_OFFERS_PER_TURN as MAX_NEGOTIATIONS_PER_TURN


def partner_of(state: GameState, index: int) -> Optional[int]:
    return state.partners[index] if state.partners else None


def _pair_partners(state: GameState, owner: int, town: str) -> set:
    pair = next((p for p in state.economy.pairs if town in p), (town,))
    squares = [i for t in pair for i in state.board.towns[t] if state.owners[i] == owner]
    return {partner_of(state, i) for i in squares} - {None}


def can_share(state: GameState, me: int, index: int) -> bool:
    square, owner = state.board.squares[index], state.owners[index]
    if square.kind != "district" or owner is None or owner == me or state.players[owner].out:
        return False
    if state.offers >= MAX_NEGOTIATIONS_PER_TURN:
        return False
    town = state.board.towns[square.town]
    ready = state.economy.houses_before_stall
    if not owns_whole_town(state.board, state.owners, square.town, owner) or state.buildings[index] != ready:
        return False
    if any(state.buildings[i] < ready for i in town) or state.stalls_left <= 0:
        return False
    if state.players[me].cash < house_cost(state, index) // 2:
        return False
    return _pair_partners(state, owner, square.town) <= {me}


def request(state: GameState, index: int) -> Tuple[GameState, Tuple[Event, ...]]:
    me = state.current
    state = replace(state, pending="stall_request", stall_request=(me, index), offers=state.offers + 1)
    return state, (Event("stall_requested", me, (("square", index), ("owner", state.owners[index]))),)


def owner_can_pay(state: GameState) -> bool:
    _, index = state.stall_request
    cost = house_cost(state, index)
    return state.players[state.owners[index]].cash >= cost - cost // 2


def accept(state: GameState) -> Tuple[GameState, Tuple[Event, ...]]:
    requester, index = state.stall_request
    owner, cost = state.owners[index], house_cost(state, index)
    state = change_cash(change_cash(state, requester, -(cost // 2)), owner, -(cost - cost // 2))
    state = replace(state, buildings=set_at(state.buildings, index, STALL), partners=set_at(state.partners, index, requester),
                    stalls_left=state.stalls_left - 1, houses_left=state.houses_left + state.economy.houses_before_stall,
                    pending="roll", stall_request=None)
    return state, (Event("stall_shared", owner, (("square", index), ("partner", requester), ("bank", -cost))),)


def refuse(state: GameState) -> Tuple[GameState, Tuple[Event, ...]]:
    requester, index = state.stall_request
    state = replace(state, pending="roll", stall_request=None)
    return state, (Event("stall_refused", state.owners[index], (("square", index), ("requester", requester))),)


def refund_partner(state: GameState, index: int) -> Tuple[GameState, Tuple[Event, ...]]:
    """The owner takes his shared stall down: he refunds the partner's half first, and the partnership ends."""
    partner = partner_of(state, index)
    if partner is None:
        return state, ()
    owner, half = state.owners[index], house_cost(state, index) // 2
    state = change_cash(change_cash(state, owner, -half), partner, half)
    state = replace(state, partners=set_at(state.partners, index, None))
    return state, (Event("partner_refunded", owner, (("to", partner), ("amount", half))),)
