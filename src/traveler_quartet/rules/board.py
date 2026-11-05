import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Square:
    kind: str
    name: str
    town: Optional[str] = None
    price: int = 0


@dataclass(frozen=True)
class Board:
    squares: Tuple[Square, ...]
    towns: Mapping[str, Tuple[int, ...]]


def _towns(squares: Tuple[Square, ...]) -> Mapping[str, Tuple[int, ...]]:
    towns = {}
    for index, square in enumerate(squares):
        if square.town is not None:
            towns.setdefault(square.town, []).append(index)
    return MappingProxyType({town: tuple(indices) for town, indices in towns.items()})


def load_board(path: Path = DATA_DIR / "board.json") -> Board:
    raw = json.loads(path.read_text(encoding="utf-8"))
    squares = tuple(Square(**square) for square in raw["squares"])
    if len(squares) != 40:
        raise ValueError(f"a board has 40 squares, this one has {len(squares)}")
    return Board(squares=squares, towns=_towns(squares))
