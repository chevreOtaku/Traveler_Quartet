from typing import Tuple

from traveler_quartet.rules.economy import STALL, mortgage_value
from traveler_quartet.rules.state import GameState


def _buildings_value(state: GameState, index: int) -> int:
    level = state.buildings[index]
    cost = state.economy.house_costs[state.board.squares[index].town]
    if level == STALL:
        return cost * (state.economy.houses_before_stall + 1)
    return cost * level


def _district_value(state: GameState, index: int) -> int:
    if state.mortgaged[index]:
        return mortgage_value(state.board, state.economy, index)
    return state.board.squares[index].price + _buildings_value(state, index)


def net_worth(state: GameState, player: int) -> int:
    if state.players[player].out:
        return 0
    owned = (i for i, owner in enumerate(state.owners) if owner == player)
    return state.players[player].cash + sum(_district_value(state, i) for i in owned)


def ranking(state: GameState) -> Tuple[Tuple[int, int], ...]:
    """(player, net worth), richest first; a tie keeps the seating order."""
    worths = [(player, net_worth(state, player)) for player in range(len(state.players))]
    return tuple(sorted(worths, key=lambda pair: -pair[1]))
