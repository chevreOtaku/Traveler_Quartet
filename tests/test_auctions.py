from dataclasses import replace

from factory import cash, game
from test_specials import _landing_on
from traveler_quartet.rules.engine import actor, apply, legal_actions


def _auction(players: int = 3):
    state = _landing_on(8, start=0)
    state = replace(state, players=state.players + tuple(state.players[0] for _ in range(players - len(state.players))))
    state, _ = apply(state, "roll")
    state, _ = apply(state, "pass")
    return state


def test_declining_a_free_district_opens_an_auction_for_everyone():
    state = _auction()
    assert state.pending == "auction"
    assert actor(state) == 0
    assert set(legal_actions(state)) == {"raise:5", "raise:10", "raise:25", "drop"}


def test_the_last_bidder_standing_buys_at_the_last_price():
    state = _auction()
    state, _ = apply(state, "raise:10")
    assert actor(state) == 1
    state, _ = apply(state, "drop")
    assert actor(state) == 2
    state, events = apply(state, "drop")
    assert state.owners[8] == 0 and state.players[0].cash == 750 - 10
    assert state.pending != "auction"
    assert any(e.kind == "auction_won" for e in events)


def test_a_bidder_who_dropped_does_not_come_back():
    state = _auction()
    state, _ = apply(state, "drop")
    state, _ = apply(state, "raise:5")
    assert actor(state) == 2
    state, _ = apply(state, "raise:5")
    assert actor(state) == 1


def test_nobody_bidding_leaves_the_district_free():
    state = _auction()
    for _ in range(3):
        state, _ = apply(state, "drop")
    assert state.owners[8] is None and state.pending != "auction"


def test_a_bid_cannot_go_above_the_bidder_cash():
    state = cash(_auction(), 0, 12)
    assert set(legal_actions(state)) == {"raise:5", "raise:10", "drop"}


def test_the_only_bidder_left_without_a_bid_may_still_buy():
    state = _auction()
    state, _ = apply(state, "drop")
    state, _ = apply(state, "drop")
    assert actor(state) == 2 and "raise:5" in legal_actions(state)
    state, _ = apply(state, "raise:5")
    assert state.owners[8] == 2 and state.players[2].cash == 750 - 5


def test_an_unaffordable_district_also_goes_to_auction():
    state = cash(_landing_on(8, start=0), 0, 1)
    state, _ = apply(state, "roll")
    assert state.pending == "auction"
