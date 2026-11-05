from dataclasses import replace

from factory import BROWN, build_levels, cash, game, own
from traveler_quartet.rules.endgame import net_worth, ranking


def test_net_worth_counts_cash_districts_and_buildings():
    state = build_levels(own(game(), 0, *BROWN), {1: 2, 3: 4})
    assert net_worth(state, 0) == 750 + 30 + 30 + 2 * 25 + (3 * 25 + 25)


def test_a_mortgaged_district_counts_for_half():
    state = replace(own(game(), 0, 37), mortgaged=tuple(i == 37 for i in range(40)))
    assert net_worth(state, 0) == 750 + 87


def test_the_ranking_puts_the_richest_first():
    state = cash(cash(game(players=3), 0, 100), 2, 900)
    assert [player for player, _ in ranking(state)] == [2, 1, 0]
