from dataclasses import replace
from typing import Dict, Optional

from traveler_quartet.rules.engine import GameState, new_game

BROWN = (1, 3)
ORANGE = (16, 18, 19)


def game(players: int = 2, seed: int = 1) -> GameState:
    return new_game(seed=seed, player_count=players)


def own(state: GameState, player: Optional[int], *squares: int) -> GameState:
    owners = list(state.owners)
    for square in squares:
        owners[square] = player
    return replace(state, owners=tuple(owners))


def build_levels(state: GameState, levels: Dict[int, int]) -> GameState:
    table = list(state.buildings)
    for square, level in levels.items():
        table[square] = level
    return replace(state, buildings=tuple(table))


def cash(state: GameState, player: int, amount: int) -> GameState:
    players = list(state.players)
    players[player] = replace(players[player], cash=amount)
    return replace(state, players=tuple(players))


def at(state: GameState, player: int, square: int) -> GameState:
    players = list(state.players)
    players[player] = replace(players[player], position=square)
    return replace(state, players=tuple(players))
