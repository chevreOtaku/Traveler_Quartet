import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

from traveler_quartet.rules.board import DATA_DIR, Board

Owners = Tuple[Optional[int], ...]
STALL = 4


@dataclass(frozen=True)
class Economy:
    start_cash: int
    salary: int
    rounds: int
    rent_percent: int
    rent_multiplier_bare: int
    rent_multiplier_whole_town: int
    rent_multipliers_by_level: Tuple[int, ...]
    house_costs: Mapping[str, int]
    houses_stock: int
    stalls_stock: int
    houses_before_stall: int
    sell_back_percent: int
    mortgage_percent: int
    unmortgage_interest_percent: int
    pairs: Tuple[Tuple[str, str], ...]
    pair_bonus: int
    stall_income_own: int
    portal_rent: int
    portal_rent_all: int
    utility_multiplier: int
    utility_multiplier_both: int
    dungeon_exit_cost: int
    dungeon_turns: int
    doubles_to_dungeon: int
    card_values: Mapping[str, int]
    stall_income_shared: int


def load_economy(path: Path = DATA_DIR / "economy.json") -> Economy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["rent_multipliers_by_level"] = tuple(raw["rent_multipliers_by_level"])
    raw["pairs"] = tuple(tuple(pair) for pair in raw["pairs"])
    return Economy(**raw)


def owns_whole_town(board: Board, owners: Owners, town: str, player: int) -> bool:
    return all(owners[index] == player for index in board.towns[town])


def mortgage_value(board: Board, economy: Economy, index: int) -> int:
    return board.squares[index].price * economy.mortgage_percent // 100


def rent(board: Board, economy: Economy, owners: Owners, index: int,
         buildings: Optional[Tuple[int, ...]] = None, mortgaged: Optional[Tuple[bool, ...]] = None) -> int:
    square = board.squares[index]
    owner = owners[index]
    if square.kind != "district" or owner is None or (mortgaged and mortgaged[index]):
        return 0
    base = square.price * economy.rent_percent // 100
    level = buildings[index] if buildings else 0
    if level:
        return base * economy.rent_multipliers_by_level[level]
    whole = owns_whole_town(board, owners, square.town, owner)
    return base * (economy.rent_multiplier_whole_town if whole else economy.rent_multiplier_bare)
