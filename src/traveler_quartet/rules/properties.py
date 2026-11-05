from typing import Tuple

from traveler_quartet.rules.economy import rent as district_rent
from traveler_quartet.rules.state import GameState

PROPERTY_KINDS = ("district", "portal", "utility")


def is_property(state: GameState, index: int) -> bool:
    return state.board.squares[index].kind in PROPERTY_KINDS


def _owned_of_kind(state: GameState, kind: str, owner: int) -> Tuple[int, int]:
    of_kind = [i for i, s in enumerate(state.board.squares) if s.kind == kind]
    return sum(1 for i in of_kind if state.owners[i] == owner), len(of_kind)


def property_rent(state: GameState, index: int, dice: Tuple[int, int]) -> int:
    """The rent of any property: a district by its formula; a portal 15, or 50 if its owner holds all four; a utility
    the dice times 2, or 5 if its owner holds both. A mortgaged property pays nothing."""
    owner, kind = state.owners[index], state.board.squares[index].kind
    if owner is None or state.mortgaged[index]:
        return 0
    if kind == "district":
        return district_rent(state.board, state.economy, state.owners, index, state.buildings, state.mortgaged)
    owned, total = _owned_of_kind(state, kind, owner)
    economy = state.economy
    if kind == "portal":
        return economy.portal_rent_all if owned == total else economy.portal_rent
    multiplier = economy.utility_multiplier_both if owned == total else economy.utility_multiplier
    return sum(dice) * multiplier
