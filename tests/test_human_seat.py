"""A HUMAN seat (D51): played from afar like a remote seat -- a token, the computers wait for it -- and DECLARED, so a
spectator knows which pawns a human moves (a front shows those moves up close). The public snapshot says each seat's
kind, never a token nor a computer's level."""

import json

import pytest

from traveler_quartet.match.server import Registry, handle
from traveler_quartet.match.session import act, new_session, watched
from traveler_quartet.rules.engine import actor


def test_a_human_seat_gets_a_token_and_the_computers_wait_for_it():
    session = new_session(("human", "normal", "remote", "easy"), seed=1, make_token=iter(["h", "r"]).__next__)
    assert session.tokens == {"h": 0, "r": 2}
    assert actor(session.state) == 0 and session.revision == 0
    act(session, "h", "roll")
    assert actor(session.state) in (0, 2) or session.state.over


def test_the_public_snapshot_names_each_seat_kind_and_nothing_more():
    session = new_session(("human", "hard", "remote", "normal"), seed=2, make_token=iter(["h", "r"]).__next__)
    snapshot = watched(session)
    assert snapshot["seats"] == ["human", "computer", "remote", "computer"]
    text = json.dumps(snapshot)
    assert "hard" not in json.dumps(snapshot["seats"]) and '"h"' not in text and '"r"' not in text


def test_an_unknown_seat_kind_is_refused():
    with pytest.raises(ValueError, match="human"):
        new_session(("robot", "normal"), seed=1)


def test_the_server_creates_a_game_with_a_human_and_publishes_the_kinds():
    registry = Registry()
    status, created = handle(registry, "POST", "/games", {}, json.dumps({"seats": ["human", "normal"], "seed": 3,
                                                                          "rounds": 2}).encode())
    assert status == 201 and list(created["tokens"].values()) == [0]
    status, snapshot = handle(registry, "GET", f"/games/{created['game']}/public", {}, b"")
    assert status == 200 and snapshot["seats"] == ["human", "computer"]
