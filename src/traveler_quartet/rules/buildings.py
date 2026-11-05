from dataclasses import replace
from typing import Tuple

from traveler_quartet.rules.economy import STALL, owns_whole_town
from traveler_quartet.rules.state import Event, GameState, Step, change_cash, set_at


def _town_of(state: GameState, index: int) -> Tuple[int, ...]:
    return state.board.towns[state.board.squares[index].town]


def _levels(state: GameState, town: Tuple[int, ...]) -> Tuple[int, ...]:
    return tuple(state.buildings[i] for i in town)


def house_cost(state: GameState, index: int) -> int:
    return state.economy.house_costs[state.board.squares[index].town]


def can_build(state: GameState, player: int, index: int) -> bool:
    square = state.board.squares[index]
    if square.kind != "district" or state.owners[index] != player:
        return False
    town = _town_of(state, index)
    if not owns_whole_town(state.board, state.owners, square.town, player):
        return False
    if any(state.mortgaged[i] for i in town) or state.players[player].cash < house_cost(state, index):
        return False
    level, levels = state.buildings[index], _levels(state, town)
    if level >= STALL or level != min(levels):
        return False
    if level < state.economy.houses_before_stall:
        return state.houses_left > 0
    return state.stalls_left > 0


def can_sell(state: GameState, player: int, index: int) -> bool:
    if state.owners[index] != player or state.buildings[index] == 0:
        return False
    level = state.buildings[index]
    if level == STALL and state.houses_left < state.economy.houses_before_stall:
        return False
    return level == max(_levels(state, _town_of(state, index)))


def build(state: GameState, index: int) -> Step:
    me, cost = state.current, house_cost(state, index)
    level = state.buildings[index] + 1
    if level == STALL:
        state = replace(state, stalls_left=state.stalls_left - 1,
                        houses_left=state.houses_left + state.economy.houses_before_stall)
    else:
        state = replace(state, houses_left=state.houses_left - 1)
    state = change_cash(replace(state, buildings=set_at(state.buildings, index, level)), me, -cost)
    return state, (Event("built", me, (("square", index), ("level", level), ("bank", -cost))),)


def sell(state: GameState, index: int) -> Step:
    me = state.current
    refund = house_cost(state, index) * state.economy.sell_back_percent // 100
    level = state.buildings[index]
    if level == STALL:
        state = replace(state, stalls_left=state.stalls_left + 1,
                        houses_left=state.houses_left - state.economy.houses_before_stall)
    else:
        state = replace(state, houses_left=state.houses_left + 1)
    state = change_cash(replace(state, buildings=set_at(state.buildings, index, level - 1)), me, refund)
    return state, (Event("sold", me, (("square", index), ("level", level - 1), ("bank", refund))),)


def town_has_buildings(state: GameState, index: int) -> bool:
    return any(_levels(state, _town_of(state, index)))
