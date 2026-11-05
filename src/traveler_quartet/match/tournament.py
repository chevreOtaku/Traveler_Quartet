from statistics import mean, median
from typing import Dict, Sequence, Tuple

from traveler_quartet.match.runner import TimedEvent, play_game_rounds
from traveler_quartet.players.bots import BOTS
from traveler_quartet.rules.economy import owns_whole_town
from traveler_quartet.rules.endgame import ranking
from traveler_quartet.rules.engine import GameState, new_game

NEVER = 31


def _first_house_round(timed: Tuple[TimedEvent, ...]) -> int:
    return next((round_ for round_, event in timed if event.kind == "built"), NEVER)


def _has_whole_pair(state: GameState) -> bool:
    return any(all(owns_whole_town(state.board, state.owners, town, player) for town in pair)
               for pair in state.economy.pairs for player in range(len(state.players)))


def _one_game(seed: int, seats: Sequence[str]) -> Dict[str, object]:
    final, timed = play_game_rounds(new_game(seed=seed, player_count=len(seats)), [BOTS[s] for s in seats])
    return {
        "first_house": _first_house_round(timed),
        "houses": sum(1 for _, e in timed if e.kind == "built"),
        "whole_pair": _has_whole_pair(final),
        "bankruptcies": sum(1 for _, e in timed if e.kind == "bankrupt"),
        "rounds": final.round,
        "winner": ranking(final)[0][0],
    }


def run_tournament(games: int, first_seed: int, seats: Sequence[str]) -> Dict[str, object]:
    """`games` games between the computers named in `seats`, seeds first_seed, first_seed + 1, ..."""
    results = [_one_game(first_seed + n, seats) for n in range(games)]
    wins = [0] * len(seats)
    for result in results:
        wins[result["winner"]] += 1
    return {
        "games": games,
        "seats": list(seats),
        "first_house_round_median": median(r["first_house"] for r in results),
        "games_with_a_house": sum(r["first_house"] < NEVER for r in results) / games,
        "games_with_a_whole_pair": sum(r["whole_pair"] for r in results) / games,
        "buildings_per_game_mean": round(mean(r["houses"] for r in results), 2),
        "bankruptcies_per_game_mean": round(mean(r["bankruptcies"] for r in results), 2),
        "rounds_mean": round(mean(r["rounds"] for r in results), 2),
        "wins_by_seat": wins,
    }
