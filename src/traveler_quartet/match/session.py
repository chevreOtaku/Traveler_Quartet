"""A game SESSION (step 7a) -- the server's game, designed as if the players were FAR.

One token per REMOTE seat (a human or an AI at a distance); the COMPUTER seats play by themselves until a remote player
must answer; every answer is checked by the engine. A player reads only HIS view (`players/view.py`) and HIS log: when
another player draws a card he may KEEP (the rope, the mirror, the curse), the log says he drew a kept card, not which
-- otherwise the log would reveal what the view hides.
"""

import secrets
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from traveler_quartet.match.tournament import COMPUTERS
from traveler_quartet.players.recent import public_event, sentence
from traveler_quartet.players.text import render
from traveler_quartet.players.view import spectator, view
from traveler_quartet.rules.engine import GameState, actor, apply, legal_actions, new_game
from traveler_quartet.rules.state import Event

REMOTE = "remote"
MAX_COMPUTER_STEPS = 20000


class Unauthorized(ValueError):
    """An unknown token."""


class NotYourTurn(ValueError):
    """A remote player answered while another one must."""


class StaleRevision(ValueError):
    """An action sent for a revision that is no longer the current one (an old click, a retried request)."""


@dataclass
class Session:
    """`revision` (transport, never the rules): 0 at creation, +1 per SUCCESSFUL action, computer or remote, with or
    without events. Each log entry is (round, event, the revision of the action that produced it)."""
    state: GameState
    seats: Tuple[str, ...]
    tokens: Dict[str, int]
    log: List[Tuple[int, Event, int]] = field(default_factory=list)
    revision: int = 0


def _record(session: Session, round_now: int, events) -> None:
    """One successful action: the revision moves on, even when the action emitted no event."""
    session.revision += 1
    session.log.extend((round_now, e, session.revision) for e in events)


def _advance(session: Session) -> None:
    """The computers play until a remote seat must answer (or the game is over)."""
    for _ in range(MAX_COMPUTER_STEPS):
        if session.state.over or session.seats[actor(session.state)] == REMOTE:
            return
        answer = COMPUTERS[session.seats[actor(session.state)]](session.state, legal_actions(session.state))
        action = answer[0] if isinstance(answer, tuple) else answer
        round_now = session.state.round
        session.state, events = apply(session.state, action)
        _record(session, round_now, events)
    raise RuntimeError(f"the computers did not hand over in {MAX_COMPUTER_STEPS} steps")


def new_session(seats: Sequence[str], seed: int, make_token: Callable[[], str] = lambda: secrets.token_urlsafe(16),
                rounds: Optional[int] = None) -> Session:
    """`rounds`: another game length (a short game to try things; the rules keep theirs)."""
    unknown = [s for s in seats if s != REMOTE and s not in COMPUTERS]
    if unknown:
        raise ValueError(f"unknown seats {unknown}; use {REMOTE!r} or one of {sorted(COMPUTERS)}")
    tokens = {make_token(): seat for seat, kind in enumerate(seats) if kind == REMOTE}
    state = new_game(seed=seed, player_count=len(seats))
    if rounds is not None:
        state = replace(state, economy=replace(state.economy, rounds=rounds))
    session = Session(state, tuple(seats), tokens)
    _advance(session)
    return session


def _seat_of(session: Session, token: str) -> int:
    if token not in session.tokens:
        raise Unauthorized("unknown token")
    return session.tokens[token]


def act(session: Session, token: str, action: str, message: Optional[str] = None,
        expected_revision: Optional[int] = None) -> None:
    """`expected_revision`: if given and no longer current, the action is REFUSED before anything happens -- an old
    click or a retried request is never applied twice. A refused or illegal action changes nothing."""
    seat = _seat_of(session, token)
    if expected_revision is not None and expected_revision != session.revision:
        raise StaleRevision(f"stale revision {expected_revision}: the game is at revision {session.revision}")
    if session.state.over or actor(session.state) != seat:
        raise NotYourTurn(f"player {seat} cannot act now")
    round_now = session.state.round
    session.state, events = apply(session.state, action)
    said = (Event("said", seat, (("action", action), ("text", message))),) if message else ()
    _record(session, round_now, said + tuple(events))
    _advance(session)


def _logged(session: Session, viewer, since: int, until: Optional[int]) -> List[Dict[str, object]]:
    """The log as `viewer` may read it, from `since` up to `until` EXCLUDED, each event with its revision and its
    SENTENCE -- written from the FILTERED event, so it can never say more than the event shows."""
    names = [square.name for square in session.state.board.squares]
    end = len(session.log) if until is None else min(until, len(session.log))
    rows = []
    for i in range(max(since, 0), end):
        r, e, revision = session.log[i]
        shown = public_event(session.state.catalog, e, viewer)
        rows.append({"index": i, "round": r, "revision": revision, **shown, "sentence": sentence(shown, names, viewer)})
    return rows


def events_for(session: Session, token: str, since: int = 0, until: Optional[int] = None) -> List[Dict[str, object]]:
    return _logged(session, _seat_of(session, token), since, until)


def public_events(session: Session, since: int = 0, until: Optional[int] = None) -> List[Dict[str, object]]:
    """The log for a SPECTATOR: everyone's kept cards stay "a kept card" (no seat to be the exception)."""
    return _logged(session, None, since, until)


def watched(session: Session) -> Dict[str, object]:
    """What a spectator receives: the public view, no text to act on, no token -- one snapshot (view, revision,
    log_length): render it with exactly the events below `log_length`."""
    return {"view": spectator(session.state), "over": session.state.over, "revision": session.revision,
            "log_length": len(session.log)}


def seen(session: Session, token: str) -> Dict[str, object]:
    seat = _seat_of(session, token)
    me = view(session.state, seat)
    return {"view": me, "text": render(me), "over": session.state.over, "revision": session.revision,
            "log_length": len(session.log)}
