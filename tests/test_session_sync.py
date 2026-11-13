"""Synchronization for a front (contract v2, PR B, agreed with the front 07/11). A session `revision`: 0 at creation
before the computers' first moves, +1 per SUCCESSFUL action (computer or remote, with or without events), +0 for a
refused one. Every logged event carries the revision of its action. A snapshot gives (view, revision, log_length) under
one lock; events can be read with an EXCLUSIVE `until` bound, so a front renders exactly the events of its snapshot.
`expected_revision` on an action refuses a stale click (409) without any effect."""

import json

import pytest

from traveler_quartet.match import session as session_module
from traveler_quartet.match.server import Registry, handle
from traveler_quartet.match.session import new_session


def _tokens():
    numbers = iter(range(100))
    return lambda: f"t{next(numbers)}"


def _game(reg, seats):
    _, created = handle(reg, "POST", "/games", {}, json.dumps({"seats": seats, "seed": 1}).encode())
    return created["game"], {seat: token for token, seat in created["tokens"].items()}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _act(reg, game, token, body):
    return handle(reg, "POST", f"/games/{game}/act", _auth(token), json.dumps(body).encode())


def test_the_revision_counts_every_successful_action_and_nothing_else(monkeypatch):
    applied = []
    real = session_module.apply

    def counting(state, action):
        result = real(state, action)
        applied.append(action)
        return result
    monkeypatch.setattr(session_module, "apply", counting)
    s = new_session(("normal", "remote", "normal"), seed=3, make_token=_tokens())
    assert s.revision == len(applied) > 0
    token = next(iter(s.tokens))
    session_module.act(s, token, "roll")
    assert s.revision == len(applied)


def test_an_eventless_action_still_moves_the_revision():
    """A sealed bid that is not the last one emits NO event (it must reveal nothing) -- it is still an action."""
    from dataclasses import replace
    from traveler_quartet.rules.auctions import Sealed
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote", "remote"])
    session = reg.games[game]
    session.state = replace(session.state, pending="sealed", current=0,
                            sealed=Sealed(queue=(6,), bidders=(0, 1, 2), turn=0, bids=()))
    before = (session.revision, len(session.log))
    assert _act(reg, game, tokens[0], {"action": "bid:20"})[0] == 200
    assert session.revision == before[0] + 1 and len(session.log) == before[1]


def test_a_fresh_game_with_a_remote_first_seat_is_at_revision_zero():
    assert new_session(("remote", "normal"), seed=1, make_token=_tokens()).revision == 0


def test_a_refused_action_changes_neither_revision_nor_log():
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote"])
    before = handle(reg, "GET", f"/games/{game}/view", _auth(tokens[0]), b"")[1]
    assert _act(reg, game, tokens[0], {"action": "fly", "message": "hello"})[0] == 400
    after = handle(reg, "GET", f"/games/{game}/view", _auth(tokens[0]), b"")[1]
    assert (after["revision"], after["log_length"]) == (before["revision"], before["log_length"])


def test_every_event_of_one_action_shares_its_revision():
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote"])
    _act(reg, game, tokens[0], {"action": "roll", "message": "go"})
    rows = handle(reg, "GET", f"/games/{game}/events?since=0", _auth(tokens[0]), b"")[1]["events"]
    assert rows and {row["revision"] for row in rows if row["round"] == 1} == {1}
    assert rows[0]["kind"] == "said"


def test_a_snapshot_and_an_until_bound_give_exactly_its_events():
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote"])
    _act(reg, game, tokens[0], {"action": "roll"})
    snapshot = handle(reg, "GET", f"/games/{game}/public", {}, b"")[1]
    length, actor = snapshot["log_length"], snapshot["view"]["actor"]
    legal = handle(reg, "GET", f"/games/{game}/view", _auth(tokens[actor]), b"")[1]["view"]["legal_actions"]
    assert _act(reg, game, tokens[actor], {"action": legal[0], "message": "later"})[0] == 200
    bounded = handle(reg, "GET", f"/games/{game}/public/events?since=0&until={length}", {}, b"")[1]["events"]
    everything = handle(reg, "GET", f"/games/{game}/public/events?since=0", {}, b"")[1]["events"]
    assert len(everything) > length and [row["index"] for row in bounded] == list(range(length))
    assert snapshot["revision"] >= 1


def test_a_stale_expected_revision_is_refused_without_any_effect():
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote"])
    now = handle(reg, "GET", f"/games/{game}/view", _auth(tokens[0]), b"")[1]
    stale = _act(reg, game, tokens[0], {"action": "roll", "message": "x", "expected_revision": now["revision"] + 5})
    after = handle(reg, "GET", f"/games/{game}/view", _auth(tokens[0]), b"")[1]
    assert stale[0] == 409 and "revision" in stale[1]["error"]
    assert (after["revision"], after["log_length"]) == (now["revision"], now["log_length"])
    fresh = _act(reg, game, tokens[0], {"action": "roll", "expected_revision": now["revision"]})
    assert fresh[0] == 200 and fresh[1]["revision"] == now["revision"] + 1


def test_a_retried_request_after_a_lost_reply_is_not_applied_twice():
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote"])
    now = handle(reg, "GET", f"/games/{game}/view", _auth(tokens[0]), b"")[1]["revision"]
    first = _act(reg, game, tokens[0], {"action": "roll", "expected_revision": now})
    again = _act(reg, game, tokens[0], {"action": "roll", "expected_revision": now})
    assert first[0] == 200 and again[0] == 409


@pytest.mark.parametrize("bad", ["one", 1.5, True, -1])
def test_a_malformed_expected_revision_is_a_bad_request(bad):
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote"])
    assert _act(reg, game, tokens[0], {"action": "roll", "expected_revision": bad})[0] == 400


def test_an_old_caller_without_expected_revision_still_plays():
    reg = Registry()
    game, tokens = _game(reg, ["remote", "remote"])
    assert _act(reg, game, tokens[0], {"action": "roll"})[0] == 200
