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


@dataclass
class Session:
    state: GameState
    seats: Tuple[str, ...]
    tokens: Dict[str, int]
    log: List[Tuple[int, Event]] = field(default_factory=list)


def _advance(session: Session) -> None:
    """The computers play until a remote seat must answer (or the game is over)."""
    for _ in range(MAX_COMPUTER_STEPS):
        if session.state.over or session.seats[actor(session.state)] == REMOTE:
            return
        answer = COMPUTERS[session.seats[actor(session.state)]](session.state, legal_actions(session.state))
        action = answer[0] if isinstance(answer, tuple) else answer
        round_now = session.state.round
        session.state, events = apply(session.state, action)
        session.log.extend((round_now, e) for e in events)
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


def act(session: Session, token: str, action: str, message: Optional[str] = None) -> None:
    seat = _seat_of(session, token)
    if session.state.over or actor(session.state) != seat:
        raise NotYourTurn(f"player {seat} cannot act now")
    round_now = session.state.round
    session.state, events = apply(session.state, action)
    said = (Event("said", seat, (("action", action), ("text", message))),) if message else ()
    session.log.extend((round_now, e) for e in said + tuple(events))
    _advance(session)


def _logged(session: Session, viewer, since: int) -> List[Dict[str, object]]:
    """The log as `viewer` may read it, each event with its SENTENCE -- written from the FILTERED event, so a sentence
    can never say more than the event shows (a seat reads "you", a spectator never does)."""
    names = [square.name for square in session.state.board.squares]
    rows = []
    for i, (r, e) in enumerate(session.log):
        if i >= since:
            shown = public_event(session.state.catalog, e, viewer)
            rows.append({"index": i, "round": r, **shown, "sentence": sentence(shown, names, viewer)})
    return rows


def events_for(session: Session, token: str, since: int = 0) -> List[Dict[str, object]]:
    return _logged(session, _seat_of(session, token), since)


def public_events(session: Session, since: int = 0) -> List[Dict[str, object]]:
    """The log for a SPECTATOR: everyone's kept cards stay "a kept card" (no seat to be the exception)."""
    return _logged(session, None, since)


def watched(session: Session) -> Dict[str, object]:
    """What a spectator receives: the public view, no text to act on, no token."""
    return {"view": spectator(session.state), "over": session.state.over, "log_length": len(session.log)}


def seen(session: Session, token: str) -> Dict[str, object]:
    seat = _seat_of(session, token)
    me = view(session.state, seat)
    return {"view": me, "text": render(me), "over": session.state.over, "log_length": len(session.log)}
