import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from traveler_quartet.rules.board import DATA_DIR, Board

Owners = Tuple[Optional[int], ...]


@dataclass(frozen=True)
class Economy:
    start_cash: int
    salary: int
    rounds: int
    rent_percent: int
    rent_multiplier_bare: int
    rent_multiplier_whole_town: int


def load_economy(path: Path = DATA_DIR / "economy.json") -> Economy:
    return Economy(**json.loads(path.read_text(encoding="utf-8")))


def owns_whole_town(board: Board, owners: Owners, town: str, player: int) -> bool:
    return all(owners[index] == player for index in board.towns[town])


def rent(board: Board, economy: Economy, owners: Owners, index: int) -> int:
    square = board.squares[index]
    owner = owners[index]
    if square.kind != "district" or owner is None:
        return 0
    base = square.price * economy.rent_percent // 100
    whole = owns_whole_town(board, owners, square.town, owner)
    multiplier = economy.rent_multiplier_whole_town if whole else economy.rent_multiplier_bare
    return base * multiplier
