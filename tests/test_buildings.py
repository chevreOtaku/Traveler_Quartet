from dataclasses import replace

from factory import BROWN, build_levels, game, own
from traveler_quartet.rules.engine import apply, legal_actions


def test_no_building_without_the_whole_town():
    state = own(game(), 0, 1)
    assert not any(a.startswith("build") for a in legal_actions(state))


def test_with_the_whole_town_every_district_can_get_a_house_before_rolling():
    state = own(game(), 0, *BROWN)
    assert {"build:1", "build:3"} <= set(legal_actions(state))
    assert "roll" in legal_actions(state)


def test_a_house_costs_the_town_price_and_comes_from_the_stock():
    state, events = apply(own(game(), 0, *BROWN), "build:1")
    assert state.buildings[1] == 1
    assert state.players[0].cash == 750 - 25
    assert state.houses_left == 31
    assert events[0].kind == "built"
    assert state.current == 0


def test_houses_are_built_evenly():
    state, _ = apply(own(game(), 0, *BROWN), "build:1")
    assert "build:1" not in legal_actions(state)
    assert "build:3" in legal_actions(state)


def test_after_three_houses_everywhere_the_next_build_is_a_stall():
    state = build_levels(own(game(), 0, *BROWN), {1: 3, 3: 3})
    state = replace(state, houses_left=32 - 6)
    state, _ = apply(state, "build:1")
    assert state.buildings[1] == 4
    assert state.houses_left == 32 - 3
    assert state.stalls_left == 11


def test_no_house_when_the_stock_is_empty():
    state = replace(own(game(), 0, *BROWN), houses_left=0)
    assert not any(a.startswith("build") for a in legal_actions(state))


def test_no_building_while_a_district_of_the_town_is_mortgaged():
    state = own(game(), 0, *BROWN)
    state = replace(state, mortgaged=tuple(i == 3 for i in range(40)))
    assert not any(a.startswith("build") for a in legal_actions(state))


def test_selling_a_house_refunds_half_from_the_highest_district():
    state = build_levels(own(game(), 0, *BROWN), {1: 2, 3: 1})
    assert "sell:1" in legal_actions(state)
    assert "sell:3" not in legal_actions(state)
    state, _ = apply(state, "sell:1")
    assert state.buildings[1] == 1
    assert state.players[0].cash == 750 + 12
