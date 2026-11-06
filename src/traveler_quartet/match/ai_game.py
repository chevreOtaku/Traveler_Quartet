"""One mixed table, with a decision journal saved outside repositories."""

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
import tempfile
import time
from typing import Dict, List, Mapping, Optional, Sequence
import uuid

from traveler_quartet.match.runner import TimedEvent, play_game_rounds
from traveler_quartet.match.tournament import COMPUTERS, COUNTED
from traveler_quartet.players.command_player import CLAUDE, CODEX, CommandPlayer, run_command
from traveler_quartet.rules.endgame import ranking
from traveler_quartet.rules.engine import GameState, actor, new_game

COMMANDS = {"claude": CLAUDE, "codex": CODEX}


@dataclass
class GameProgress:
    state: GameState
    timed: List[TimedEvent] = field(default_factory=list)

    def record(self, state: GameState, events: tuple) -> None:
        self.state = state
        self.timed.extend(events)


def _validate(seats: Sequence[str], rounds: Optional[int]) -> None:
    if not 2 <= len(seats) <= 4:
        raise ValueError("a table needs 2 to 4 players")
    unknown = set(seats) - set(COMPUTERS) - set(COMMANDS)
    if unknown:
        raise ValueError(f"unknown seats: {sorted(unknown)}")
    if rounds is not None and rounds < 1:
        raise ValueError("rounds must be positive")


def _log_target(log_path: Optional[Path]) -> Path:
    target = Path(log_path) if log_path is not None else (
        Path(tempfile.gettempdir()) / f"traveler-quartet-{uuid.uuid4().hex}.json")
    target = target.expanduser().resolve()
    if any((parent / ".git").exists() for parent in target.parents):
        raise ValueError("game logs must be outside every repository")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite log: {target}")
    return target


def _players(seats: Sequence[str], commands: Mapping[str, List[str]]):
    choosers, agents = [], {}
    for seat, name in enumerate(seats):
        if name in COMPUTERS:
            choosers.append(COMPUTERS[name])
        else:
            agent = CommandPlayer(run_command(commands[name]), seat=seat)
            agents[str(seat)] = agent
            choosers.append(agent)
    return choosers, agents


def _report(final, timed, seats, agents, started: float) -> dict:
    journals = {seat: agent.log for seat, agent in agents.items()}
    decisions = [decision for journal in journals.values() for decision in journal]
    counts = [{name: sum(event.player == seat and event.kind in COUNTED[name] for _, event in timed)
               for name in ("trades", "auctions", "curses")} for seat in range(len(seats))]
    return {
        "seats": list(seats), "over": final.over,
        "status": "completed" if final.over else "interrupted", "ranking_is_final": final.over,
        "rounds_limit": final.economy.rounds, "rounds_played": final.round,
        "ranking": [{"seat": seat, "player": seats[seat], "net_worth": worth}
                    for seat, worth in ranking(final)],
        "ai_decisions": journals,
        "said": [{"round": round_number, "player": event.player, **dict(event.data)}
                 for round_number, event in timed if event.kind == "said"],
        "actions_by_seat": counts,
        "illegal_then_corrected": sum(d["attempts"] - 1 for d in decisions if not d["fallback"]),
        "fallbacks": sum(d["fallback"] for d in decisions),
        "minutes": round((time.monotonic() - started) / 60, 3),
    }


def _write_report(target: Path, state, timed, seats, agents, started, seed, error=None) -> dict:
    report = {**_report(state, timed, seats, agents, started), "seed": seed, "log_path": str(target)}
    if error is not None:
        report["error"] = {"type": type(error).__name__, "message": str(error),
                           "round": state.round, "seat": actor(state), "pending": state.pending}
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return report


def play_ai_game(seats: Sequence[str], seed: int = 1, rounds: Optional[int] = None,
                 log_path: Optional[Path] = None,
                 commands: Optional[Mapping[str, List[str]]] = None) -> Dict[str, object]:
    _validate(seats, rounds)
    target = _log_target(log_path)
    initial = new_game(seed=seed, player_count=len(seats))
    if rounds is not None:
        initial = replace(initial, economy=replace(initial.economy, rounds=rounds))
    choosers, agents = _players(seats, COMMANDS if commands is None else commands)
    started = time.monotonic()
    progress = GameProgress(initial)
    try:
        final, timed = play_game_rounds(initial, choosers, on_step=progress.record)
    except Exception as error:
        _write_report(target, progress.state, progress.timed, seats, agents, started, seed, error)
        raise RuntimeError(f"game interrupted; partial log saved to {target}: {type(error).__name__}") from error
    return _write_report(target, final, timed, seats, agents, started, seed)
