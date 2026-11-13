"""A game SESSION (step 7a): the server's game, designed as if the players were FAR -- one token per remote player, the
computers play by themselves until a remote player must answer, and every answer is checked by the engine. A player
reads only HIS view, and HIS log: the others' kept cards stay hidden there too."""

import pytest

from traveler_quartet.match.session import NotYourTurn, Unauthorized, act, events_for, new_session, seen
from traveler_quartet.rules.engine import IllegalAction, actor


def _tokens():
    counter = iter(range(100))
    return lambda: f"t{next(counter)}"


def test_only_remote_seats_get_a_token():
    s = new_session(("remote", "normal", "remote"), seed=1, make_token=_tokens())
    assert sorted(s.tokens.values()) == [0, 2]


def test_the_computers_play_until_a_remote_player_must_answer():
    s = new_session(("normal", "remote"), seed=1, make_token=_tokens())
    assert not s.state.over and s.seats[actor(s.state)] == "remote"
    assert any(e.player == 0 for _, e, _ in s.log)    # the computer at seat 0 has already played


def test_an_unknown_token_is_refused():
    s = new_session(("remote", "normal"), seed=1, make_token=_tokens())
    with pytest.raises(Unauthorized):
        act(s, "nope", "roll")


def test_a_player_cannot_act_when_it_is_not_his_turn():
    s = new_session(("remote", "remote"), seed=1, make_token=_tokens())
    waiting = next(t for t, seat in s.tokens.items() if seat != actor(s.state))
    with pytest.raises(NotYourTurn):
        act(s, waiting, "roll")


def test_an_illegal_action_is_refused_by_the_engine():
    s = new_session(("remote", "normal"), seed=1, make_token=_tokens())
    with pytest.raises(IllegalAction):
        act(s, "t0", "fly")


def test_a_legal_action_moves_the_game_and_its_message_is_logged():
    s = new_session(("remote", "normal"), seed=1, make_token=_tokens())
    before = s.state
    act(s, "t0", "roll", "here I go")
    assert s.state != before
    assert any(e["kind"] == "said" and e["data"]["text"] == "here I go" for e in events_for(s, "t0"))


def test_a_player_sees_his_own_view_through_his_token():
    s = new_session(("remote", "remote"), seed=1, make_token=_tokens())
    assert seen(s, "t1")["view"]["me"]["seat"] == 1 and "Round 1" in seen(s, "t1")["text"]


def test_the_others_kept_cards_stay_hidden_in_the_log_too():
    from traveler_quartet.players.recent import public_event
    from traveler_quartet.rules.state import Event
    s = new_session(("remote", "remote"), seed=1, make_token=_tokens())
    catalog = s.state.catalog
    drawn = Event("card", 1, (("card", "mirror"), ("deck", "chance")))
    assert public_event(catalog, drawn, viewer=1)["data"]["card"] == "mirror"
    assert public_event(catalog, drawn, viewer=0)["data"] == {"card": "a kept card"}
    plain = Event("card", 1, (("card", "gain_50"),))
    assert public_event(catalog, plain, viewer=0)["data"]["card"] == "gain_50"
