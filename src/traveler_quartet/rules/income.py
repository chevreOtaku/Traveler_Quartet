from traveler_quartet.rules.economy import STALL, owns_whole_town
from traveler_quartet.rules.state import GameState


def start_income(state: GameState, player: int) -> int:
    """What a player earns when he passes Start: the salary, +10 per whole pair, +20 per own stall."""
    economy = state.economy
    pairs = sum(1 for pair in economy.pairs
                if all(owns_whole_town(state.board, state.owners, town, player) for town in pair))
    stall_income = 0
    for i, owner in enumerate(state.owners):
        if state.buildings[i] != STALL:
            continue
        partner = state.partners[i] if state.partners else None
        if owner == player:
            stall_income += economy.stall_income_own if partner is None else economy.stall_income_shared
        elif partner == player:
            stall_income += economy.stall_income_shared
    return economy.salary + pairs * economy.pair_bonus + stall_income
