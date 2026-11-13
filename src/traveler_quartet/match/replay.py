"""Rebuild an AI game from its report: the seed, the rounds, the computers (deterministic) and the AI seats' logged
actions. It gives the STATE at each AI decision -- the ground truth a table message is checked against -- and it
proves itself: the replayed events must equal the report's, one by one, or it refuses."""

from dataclasses import dataclass, replace
from typing import Dict, List, Mapping, Optional, Tuple

from traveler_quartet.match.runner import TimedEvent, play_game_rounds
from traveler_quartet.match.tournament import COMPUTERS
from traveler_quartet.rules.engine import GameState, IllegalAction, negotiations, new_game


class ReplayMismatch(ValueError):
    """The report cannot be replayed faithfully: another engine, a missing decision, or a damaged log."""


@dataclass(frozen=True)
class Decision:
    seat: int
    rank: int
    state: GameState
    action: str
    message: Optional[str]


def plain(value):
    """Tuples as lists: the shape of the event data in a JSON report."""
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


class _Logged:
    """An AI seat replayed: asked only when the command player would have asked (a real choice), it answers what
    the report says it answered. Its message is read in the journal at the replay's EXACT position: the runner logs a
    message right before the events of its move -- matching by round and action alone gives a message to the wrong
    move when the same move is made twice in a round (two raises in one auction, two rolls after a double)."""

    def __init__(self, seat: int, report: Mapping, sink: List[Decision], position: Dict[str, int]):
        self.seat, self.sink, self.events, self.position = seat, sink, report["events"], position
        self.actions = [d["action"] for d in report["ai_decisions"][str(seat)]]

    def _message(self, action: str) -> Optional[str]:
        at = self.position["next"]
        event = self.events[at] if at < len(self.events) else None
        mine = event is not None and event["kind"] == "said" and event["player"] == self.seat
        return event["data"]["text"] if mine and event["data"]["action"] == action else None

    def __call__(self, state: GameState, legal: Tuple[str, ...]):
        if len(legal) == 1 and not negotiations(state):
            return legal[0]
        rank = sum(1 for d in self.sink if d.seat == self.seat)
        if rank >= len(self.actions):
            raise ReplayMismatch(f"seat {self.seat} is asked more often than the report says")
        action = self.actions[rank]
        message = self._message(action)
        self.sink.append(Decision(self.seat, rank, state, action, message))
        return (action, message) if message else action


def replay(report: Mapping) -> Tuple[Tuple[Decision, ...], Tuple[TimedEvent, ...], GameState]:
    seats = report["seats"]
    initial = new_game(seed=report["seed"], player_count=len(seats))
    initial = replace(initial, economy=replace(initial.economy, rounds=report["rounds_limit"]))
    decisions: List[Decision] = []
    position = {"next": 0}

    def advance(_state, events) -> None:
        position["next"] += len(events)

    choosers = [COMPUTERS[name] if name in COMPUTERS else _Logged(seat, report, decisions, position)
                for seat, name in enumerate(seats)]
    try:
        final, timed = play_game_rounds(initial, choosers, on_step=advance)
    except IllegalAction as error:
        raise ReplayMismatch(f"a logged action is not legal in the replay: {error}") from error
    rebuilt = [{"round": r, "kind": e.kind, "player": e.player, "data": plain(dict(e.data))} for r, e in timed]
    if rebuilt != report["events"]:
        first = next((i for i, (a, b) in enumerate(zip(rebuilt, report["events"])) if a != b),
                     min(len(rebuilt), len(report["events"])))
        raise ReplayMismatch(f"the replay leaves the report at event {first}")
    return tuple(decisions), timed, final
