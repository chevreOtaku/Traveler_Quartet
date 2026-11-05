from dataclasses import fields, replace
from statistics import mean, median
from typing import Dict, Mapping, Optional, Sequence, Tuple

from traveler_quartet.match.runner import TimedEvent, play_game_rounds
from traveler_quartet.players.bots import BOTS
from traveler_quartet.players.hard import hard
from traveler_quartet.rules.economy import owns_whole_town
from traveler_quartet.rules.endgame import ranking
from traveler_quartet.rules.engine import GameState, new_game

NEVER = 31
COUNTED = {
    "trades": ("trade_done",), "auctions": ("auction_won", "auction_unsold"), "curses": ("cursed",),
    "disasters": ("disaster",), "dungeon_stays": ("stayed_in_dungeon",), "shared_stalls": ("stall_shared",),
}
COMPUTERS = {**BOTS, "hard": hard}


def seating(seats: Sequence[str], game_number: int) -> Tuple[int, ...]:
    """Which entrant sits at each seat in game `game_number`: the seats ROTATE, so every entrant sits everywhere as often
    (the first seat wins more by itself -- without rotation, a computer's score would carry its seat)."""
    n = len(seats)
    return tuple((seat - game_number) % n for seat in range(n))


def _without_disasters(state: GameState) -> GameState:
    keep = {cid for cid, card in state.catalog.items() if card["effect"] != "disaster"}
    return replace(state, decks=tuple((deck, tuple(c for c in cards if c in keep)) for deck, cards in state.decks))


def _changed(state: GameState, changes: Mapping[str, int]) -> GameState:
    """Other amounts for a SIMULATION (the rules in economy.json keep theirs); an unknown name is refused, not ignored."""
    known = {f.name for f in fields(state.economy)}
    unknown = sorted(set(changes) - known)
    if unknown:
        raise ValueError(f"unknown amounts {unknown}; known: {sorted(known)}")
    return replace(state, economy=replace(state.economy, **changes))


def _first_house_round(timed: Tuple[TimedEvent, ...]) -> int:
    return next((round_ for round_, event in timed if event.kind == "built"), NEVER)


def _has_whole_pair(state: GameState) -> bool:
    return any(all(owns_whole_town(state.board, state.owners, town, player) for town in pair)
               for pair in state.economy.pairs for player in range(len(state.players)))


def _one_game(seed: int, seats: Sequence[str], game_number: int, disasters: bool,
              rounds: Optional[int], changes: Mapping[str, int]) -> Dict[str, object]:
    order = seating(seats, game_number)
    state = new_game(seed=seed, player_count=len(seats))
    if not disasters:
        state = _without_disasters(state)
    if rounds is not None:
        state = replace(state, economy=replace(state.economy, rounds=rounds))
    state = _changed(state, changes)
    final, timed = play_game_rounds(state, [COMPUTERS[seats[entrant]] for entrant in order])
    winner_seat = ranking(final)[0][0]
    result = {
        "first_house": _first_house_round(timed),
        "houses": sum(1 for _, e in timed if e.kind == "built"),
        "whole_pair": _has_whole_pair(final),
        "bankruptcies": sum(1 for _, e in timed if e.kind == "bankrupt"),
        "rounds": final.round,
        "winner_seat": winner_seat,
        "winner_entrant": order[winner_seat],
    }
    for name, kinds in COUNTED.items():
        result[name] = sum(1 for _, e in timed if e.kind in kinds)
    return result


def run_tournament(games: int, first_seed: int, seats: Sequence[str], disasters: bool = True,
                   rounds: Optional[int] = None, changes: Optional[Mapping[str, int]] = None) -> Dict[str, object]:
    """`games` games between the computers named in `seats` (the entrants), seeds first_seed, first_seed + 1, ...;
    the seats rotate from one game to the next. `rounds` simulates another game length (the rules keep theirs);
    `changes` other amounts, by their name in economy.json."""
    changes = dict(changes or {})
    results = [_one_game(first_seed + n, seats, n, disasters, rounds, changes) for n in range(games)]
    by_seat, by_entrant = [0] * len(seats), [0] * len(seats)
    for result in results:
        by_seat[result["winner_seat"]] += 1
        by_entrant[result["winner_entrant"]] += 1
    report = {
        "games": games,
        "seats": list(seats),
        "disasters": disasters,
        "changes": changes,
        "rounds": rounds if rounds is not None else new_game(seed=first_seed, player_count=len(seats)).economy.rounds,
        "first_house_round_median": median(r["first_house"] for r in results),
        "games_with_a_house": sum(r["first_house"] < NEVER for r in results) / games,
        "games_with_a_whole_pair": sum(r["whole_pair"] for r in results) / games,
        "buildings_per_game_mean": round(mean(r["houses"] for r in results), 2),
        "bankruptcies_per_game_mean": round(mean(r["bankruptcies"] for r in results), 2),
        "rounds_mean": round(mean(r["rounds"] for r in results), 2),
        "wins_by_seat": by_seat,
        "wins_by_entrant": by_entrant,
        "winners": [(r["winner_seat"], r["winner_entrant"]) for r in results],
    }
    for name in COUNTED:
        report[f"{name}_per_game_mean"] = round(mean(r[name] for r in results), 2)
    return report
