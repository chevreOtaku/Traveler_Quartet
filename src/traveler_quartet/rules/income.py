from traveler_quartet.rules.economy import STALL, owns_whole_town
from traveler_quartet.rules.state import GameState


def start_income(state: GameState, player: int) -> int:
    """What a player earns when he passes Start: the salary, +10 per whole pair, +20 per own stall."""
    economy = state.economy
    pairs = sum(1 for pair in economy.pairs
                if all(owns_whole_town(state.board, state.owners, town, player) for town in pair))
    stalls = sum(1 for i, owner in enumerate(state.owners) if owner == player and state.buildings[i] == STALL)
    return economy.salary + pairs * economy.pair_bonus + stalls * economy.stall_income_own
