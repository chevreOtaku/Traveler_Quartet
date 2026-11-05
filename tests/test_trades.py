from dataclasses import replace

import pytest

from factory import BROWN, build_levels, cash, game, own
from traveler_quartet.rules.engine import IllegalAction, actor, apply, legal_actions, negotiations

DARK_BLUE = (37, 39)


def _table():
    return own(own(game(players=3), 0, 1), 1, 3, 37)


def test_an_offer_can_be_sent_to_each_rival_before_rolling():
    assert {"offer:1", "offer:2"} <= set(negotiations(_table()))


def test_a_valid_offer_waits_for_its_target():
    state, _ = apply(_table(), "offer:1:40:::0:3:")
    assert state.pending == "trade" and actor(state) == 1
    assert set(legal_actions(state)) == {"accept", "refuse"} and negotiations(state) == ("counter",)


def test_an_accepted_offer_swaps_what_was_written():
    state, _ = apply(_table(), "offer:1:40:::0:3:")
    state, events = apply(state, "accept")
    assert state.owners[3] == 0 and state.players[0].cash == 710 and state.players[1].cash == 790
    assert state.pending == "roll" and actor(state) == 0
    assert any(e.kind == "trade_done" for e in events)


def test_a_refused_offer_changes_nothing():
    before = _table()
    state, _ = apply(before, "offer:1:40:::0:3:")
    state, _ = apply(state, "refuse")
    assert state.owners == before.owners and [p.cash for p in state.players] == [750, 750, 750]


def test_an_offer_outside_half_to_double_is_refused():
    with pytest.raises(IllegalAction):
        apply(_table(), "offer:1:10:::0:37:")


def test_an_empty_offer_is_refused():
    with pytest.raises(IllegalAction):
        apply(_table(), "offer:1:0:::0::")


def test_a_district_of_a_built_town_cannot_be_traded():
    state = build_levels(own(_table(), 0, *BROWN), {1: 1})
    with pytest.raises(IllegalAction):
        apply(state, "offer:1:0:3::40::")


def test_one_cannot_offer_more_gold_than_one_has():
    with pytest.raises(IllegalAction):
        apply(cash(_table(), 0, 20), "offer:1:40:::0:3:")


def test_one_cannot_ask_what_the_target_does_not_own():
    with pytest.raises(IllegalAction):
        apply(_table(), "offer:1:40:::0:6:")


def test_a_counter_offer_swaps_the_roles():
    state, _ = apply(_table(), "offer:1:40:::0:3:")
    state, _ = apply(state, "counter:0:3::55::")
    assert state.pending == "trade" and actor(state) == 0
    state, _ = apply(state, "accept")
    assert state.owners[3] == 0 and state.players[0].cash == 750 - 55


def test_after_three_counter_offers_one_can_only_accept_or_refuse():
    state, _ = apply(_table(), "offer:1:40:::0:3:")
    for answer in ("counter:0:3::55::", "counter:45:::0:3:", "counter:0:3::50::"):
        state, _ = apply(state, answer)
    assert set(legal_actions(state)) == {"accept", "refuse"} and negotiations(state) == ()


def test_a_kept_card_can_be_traded_at_its_value():
    state = replace(_table(), players=(replace(_table().players[0], cards=("rope",)),) + _table().players[1:])
    state, _ = apply(state, "offer:1:0::rope:40::")
    state, _ = apply(state, "accept")
    assert "rope" in state.players[1].cards and state.players[0].cash == 790


def test_at_most_three_offers_per_turn():
    state = _table()
    for _ in range(3):
        state, _ = apply(state, "offer:1:40:::0:3:")
        state, _ = apply(state, "refuse")
    assert negotiations(state) == ()



def test_a_template_played_bare_is_refused_not_crashed():
    with pytest.raises(IllegalAction):
        apply(_table(), "offer:1")
    state, _ = apply(_table(), "offer:1:40:::0:3:")
    with pytest.raises(IllegalAction):
        apply(state, "counter")
