from dataclasses import replace

from factory import BROWN, ORANGE, build_levels, cash, game, own
from test_finance import DARK_BLUE, _landing_on
from traveler_quartet.rules.disasters import destroy
from traveler_quartet.rules.engine import actor, apply, legal_actions, negotiations
from traveler_quartet.rules.income import start_income


def _ready(players: int = 3):
    return build_levels(own(game(players=players), 1, *BROWN), {1: 3, 3: 3})


def _shared(players: int = 3):
    state, _ = apply(_ready(players), "share_stall:1")
    state, _ = apply(state, "accept")
    return state


def test_a_rival_may_ask_to_build_a_stall_on_a_town_ready_for_one():
    assert {"share_stall:1", "share_stall:3"} <= set(legal_actions(_ready()))


def test_no_request_before_three_houses_everywhere():
    state = build_levels(own(game(players=3), 1, *BROWN), {1: 3, 3: 2})
    assert not any(a.startswith("share_stall") for a in legal_actions(state))


def test_the_owner_answers_the_request():
    state, _ = apply(_ready(), "share_stall:1")
    assert state.pending == "stall_request" and actor(state) == 1
    assert set(legal_actions(state)) == {"accept", "refuse"}


def test_an_accepted_stall_is_built_and_paid_half_each():
    state = _shared()
    assert state.buildings[1] == 4 and state.partners[1] == 0
    assert state.players[0].cash == 750 - 12 and state.players[1].cash == 750 - 13
    assert state.stalls_left == 11 and state.pending == "roll" and actor(state) == 0


def test_a_refused_request_builds_nothing():
    state, _ = apply(_ready(), "share_stall:1")
    state, _ = apply(state, "refuse")
    assert state.buildings[1] == 3 and state.partners[1] is None


def test_a_shared_stall_brings_ten_to_each_at_start():
    state = _shared()
    assert start_income(state, 1) == 100 + 10
    assert start_income(state, 0) == 100 + 10


def test_only_one_partner_per_pair():
    state = build_levels(own(_shared(), 1, *ORANGE), {16: 3, 18: 3, 19: 3})
    state = replace(state, current=2)
    assert not any(a.startswith("share_stall") for a in legal_actions(state))
    state = replace(state, current=0)
    assert "share_stall:16" in legal_actions(state)


def test_selling_a_shared_stall_refunds_the_partner_first():
    state = replace(_shared(), current=1)
    state, _ = apply(state, "sell:1")
    assert state.partners[1] is None
    assert state.players[0].cash == 750 - 12 + 12
    assert state.players[1].cash == 750 - 13 + 12 - 12


def test_a_disaster_ends_the_partnership_without_compensation():
    state = build_levels(_shared(), {3: 0})
    state, hit = destroy(state, "brown", count=1, target="expensive")
    assert hit == (1,) and state.buildings[1] == 3 and state.partners[1] is None
    assert state.players[0].cash == 750 - 12


def test_the_owner_bankruptcy_ends_his_partnerships():
    from traveler_quartet.rules.finance import bankrupt
    from traveler_quartet.rules.state import Debt
    state = replace(_shared(), current=1, pending="debt", debt=Debt(amount=999, creditor=2))
    state, _ = bankrupt(state)
    assert all(partner is None for partner in state.partners)


def test_stall_requests_share_the_three_negotiations_of_a_turn():
    state = _ready()
    for _ in range(3):
        state, _ = apply(state, "share_stall:1")
        state, _ = apply(state, "refuse")
    assert not any(a.startswith("share_stall") for a in legal_actions(state)) and negotiations(state) == ()
