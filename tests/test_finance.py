from factory import BROWN, at, build_levels, cash, game, own
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.engine import apply, legal_actions

DARK_BLUE = (37, 39)


def _landing_on(state, square):
    return at(state, 0, (square - sum(roll(state.seed, 0))) % 40)


def test_mortgaging_gives_half_the_price():
    state, _ = apply(own(game(), 0, 37), "mortgage:37")
    assert state.mortgaged[37]
    assert state.players[0].cash == 750 + 87


def test_no_mortgage_while_the_town_has_buildings():
    state = build_levels(own(game(), 0, *BROWN), {3: 1})
    assert "mortgage:1" not in legal_actions(state)


def test_lifting_a_mortgage_costs_half_the_price_plus_ten_percent():
    state, _ = apply(own(game(), 0, 37), "mortgage:37")
    state, _ = apply(state, "unmortgage:37")
    assert not state.mortgaged[37]
    assert state.players[0].cash == 750 + 87 - (87 + 8)


def test_a_rent_bigger_than_the_cash_opens_a_debt_that_assets_can_pay():
    state = own(game(), 1, *DARK_BLUE)
    state = build_levels(state, {37: 4, 39: 4})
    state = own(state, 0, 11)
    state = cash(_landing_on(state, 37), 0, 10)
    state, _ = apply(state, "roll")
    assert state.pending == "debt"
    assert "mortgage:11" in legal_actions(state)
    assert "bankrupt" not in legal_actions(state)


def test_with_nothing_left_the_only_way_out_is_bankruptcy():
    state = own(game(players=3), 1, *DARK_BLUE)
    state = build_levels(state, {37: 4, 39: 4})
    state = cash(_landing_on(state, 37), 0, 10)
    state, _ = apply(state, "roll")
    assert legal_actions(state) == ("bankrupt",)
    state, events = apply(state, "bankrupt")
    assert state.players[0].out
    assert state.players[1].cash == 750 + 10
    assert state.current == 1
    assert any(e.kind == "bankrupt" for e in events)


def test_a_bankrupt_player_gives_his_districts_back_to_the_bank():
    state = own(game(players=3), 1, *DARK_BLUE)
    state = build_levels(own(state, 0, 1), {37: 4, 39: 4})
    state = cash(_landing_on(state, 37), 0, 10)
    state, _ = apply(state, "roll")
    while legal_actions(state) != ("bankrupt",):
        state, _ = apply(state, next(a for a in legal_actions(state) if a.startswith(("sell", "mortgage"))))
    state, _ = apply(state, "bankrupt")
    assert state.owners[1] is None
    assert not state.mortgaged[1]


def test_a_rent_equal_to_the_cash_is_paid_without_a_debt():
    state = own(game(), 1, *DARK_BLUE)
    state = build_levels(state, {37: 4, 39: 4})
    state = cash(_landing_on(state, 37), 0, 17 * 40)
    state, _ = apply(state, "roll")
    assert state.pending != "debt"
    assert state.players[0].cash == 0


def test_a_stall_that_cannot_be_sold_goes_back_to_the_stock_at_bankruptcy():
    from dataclasses import replace
    state = own(game(players=3), 1, *DARK_BLUE)
    state = build_levels(state, {37: 4, 39: 4})
    state = build_levels(own(state, 0, *BROWN), {1: 4, 3: 4})
    state = replace(state, houses_left=0, stalls_left=12 - 4)
    state = cash(_landing_on(state, 37), 0, 0)
    state, _ = apply(state, "roll")
    assert legal_actions(state) == ("bankrupt",)
    state, _ = apply(state, "bankrupt")
    assert state.stalls_left == 12 - 2
    assert state.buildings[1] == 0


def test_the_game_ends_when_one_player_is_left():
    state = own(game(players=2), 1, *DARK_BLUE)
    state = build_levels(state, {37: 4, 39: 4})
    state = cash(_landing_on(state, 37), 0, 10)
    state, _ = apply(state, "roll")
    state, _ = apply(state, "bankrupt")
    assert state.over
