from dataclasses import replace
from typing import Optional

from traveler_quartet.rules.buildings import town_has_buildings
from traveler_quartet.rules.economy import STALL, mortgage_value
from traveler_quartet.rules.state import Debt, Event, GameState, Step, change_cash, set_at, with_player


def unmortgage_cost(state: GameState, index: int) -> int:
    value = mortgage_value(state.board, state.economy, index)
    return value + value * state.economy.unmortgage_interest_percent // 100


def can_mortgage(state: GameState, player: int, index: int) -> bool:
    return (state.owners[index] == player and not state.mortgaged[index]
            and state.board.squares[index].kind == "district" and not town_has_buildings(state, index))


def can_unmortgage(state: GameState, player: int, index: int) -> bool:
    return (state.owners[index] == player and state.mortgaged[index]
            and state.players[player].cash >= unmortgage_cost(state, index))


def mortgage(state: GameState, index: int) -> Step:
    me, value = state.current, mortgage_value(state.board, state.economy, index)
    state = change_cash(replace(state, mortgaged=set_at(state.mortgaged, index, True)), me, value)
    return state, (Event("mortgaged", me, (("square", index), ("bank", value))),)


def unmortgage(state: GameState, index: int) -> Step:
    me, cost = state.current, unmortgage_cost(state, index)
    state = change_cash(replace(state, mortgaged=set_at(state.mortgaged, index, False)), me, -cost)
    return state, (Event("unmortgaged", me, (("square", index), ("bank", -cost))),)


def charge(state: GameState, amount: int, creditor: Optional[int]) -> GameState:
    """Make the current player pay; if he cannot, open a debt he must settle before anything else."""
    me = state.current
    if state.players[me].cash < amount:
        return replace(state, pending="debt", debt=Debt(amount=amount, creditor=creditor))
    state = change_cash(state, me, -amount)
    return change_cash(state, creditor, amount) if creditor is not None else state


def can_settle(state: GameState) -> bool:
    return state.debt is not None and state.players[state.current].cash >= state.debt.amount


def settle(state: GameState) -> Step:
    """Pay the open debt in full; the caller has checked `can_settle`."""
    debt = state.debt
    state = charge(replace(state, debt=None), debt.amount, debt.creditor)
    return state, (Event("debt_paid", state.current, (("to", debt.creditor), ("amount", debt.amount))),)


def bankrupt(state: GameState) -> Step:
    me, debt = state.current, state.debt
    left = state.players[me].cash
    if debt.creditor is not None:
        state = change_cash(state, debt.creditor, left)
    owned = [i for i, owner in enumerate(state.owners) if owner == me]
    stalls_back = sum(1 for i in owned if state.buildings[i] == STALL)
    owners, buildings, mortgaged = state.owners, state.buildings, state.mortgaged
    for i in owned:
        owners, buildings, mortgaged = set_at(owners, i, None), set_at(buildings, i, 0), set_at(mortgaged, i, False)
    state = replace(state, owners=owners, buildings=buildings, mortgaged=mortgaged, debt=None,
                    stalls_left=state.stalls_left + stalls_back)
    state = with_player(state, me, replace(state.players[me], cash=0, out=True))
    return state, (Event("bankrupt", me, (("to", debt.creditor), ("amount", left))),)
