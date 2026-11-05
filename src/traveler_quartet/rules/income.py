from traveler_quartet.rules.economy import STALL, owns_whole_town
from traveler_quartet.rules.state import GameState


def start_income(state: GameState, player: int) -> int:
    """What a player earns when he passes Start: the salary, the bonus of each whole town (0 in the rules for now) and of
    each whole pair, the income of his stalls."""
    economy = state.economy
    pairs = sum(1 for pair in economy.pairs
                if all(owns_whole_town(state.board, state.owners, town, player) for town in pair))
    towns = sum(1 for town in state.board.towns if owns_whole_town(state.board, state.owners, town, player))
    stall_income = 0
    for i, owner in enumerate(state.owners):
        if state.buildings[i] != STALL:
            continue
        partner = state.partners[i] if state.partners else None
        if owner == player:
            stall_income += economy.stall_income_own if partner is None else economy.stall_income_shared
        elif partner == player:
            stall_income += economy.stall_income_shared
    return economy.salary + towns * economy.town_bonus + pairs * economy.pair_bonus + stall_income
