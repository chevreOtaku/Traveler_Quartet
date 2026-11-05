from factory import build_levels, cash, game, own
from test_finance import DARK_BLUE, _landing_on
from traveler_quartet.rules.engine import actor, apply, legal_actions


def _bankrupt_with(squares, players: int = 3):
    state = own(game(players=players), 1, *DARK_BLUE)
    state = build_levels(own(state, 0, *squares), {37: 4, 39: 4})
    state = cash(_landing_on(state, 37), 0, 0)
    state, _ = apply(state, "roll")
    while legal_actions(state) != ("bankrupt",):
        state, _ = apply(state, next(a for a in legal_actions(state) if a.startswith(("sell", "mortgage"))))
    state, _ = apply(state, "bankrupt")
    return state


def test_the_bank_auctions_a_bankrupt_player_districts_under_sealed_bids():
    state = _bankrupt_with((11,))
    assert state.pending == "sealed" and state.sealed.square == 11
    assert actor(state) == 1
    assert "bid:0" in legal_actions(state) and "bid:5" in legal_actions(state)


def test_the_highest_sealed_bid_wins_and_pays():
    state = _bankrupt_with((11,))
    state, _ = apply(state, "bid:20")
    assert actor(state) == 2
    state, events = apply(state, "bid:35")
    assert state.owners[11] == 2 and state.players[2].cash == 750 - 35
    assert state.pending == "roll" and actor(state) == 1


def test_a_tie_goes_to_the_first_in_the_table_order():
    state = _bankrupt_with((11,))
    state, _ = apply(state, "bid:20")
    state, _ = apply(state, "bid:20")
    assert state.owners[11] == 1


def test_no_bid_leaves_the_district_free_and_the_next_one_is_auctioned():
    state = _bankrupt_with((11, 13))
    state, _ = apply(state, "bid:0")
    state, _ = apply(state, "bid:0")
    assert state.owners[11] is None and state.sealed.square == 13


def test_a_bid_cannot_exceed_the_cash():
    state = cash(_bankrupt_with((11,)), 1, 12)
    assert [a for a in legal_actions(state)] == ["bid:0", "bid:5", "bid:10"]


def test_no_auction_when_the_game_is_over():
    state = _bankrupt_with((11,), players=2)
    assert state.over
