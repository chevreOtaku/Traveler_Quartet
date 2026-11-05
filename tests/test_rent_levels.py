from dataclasses import replace

from factory import BROWN, build_levels, game, own
from traveler_quartet.rules.economy import rent


def _rent(state, square):
    return rent(state.board, state.economy, state.owners, square, state.buildings, state.mortgaged)


def test_each_level_multiplies_the_base_rent():
    state = own(game(), 0, *BROWN)
    expected = {1: 3 * 4, 2: 3 * 10, 3: 3 * 25, 4: 3 * 40}
    for level, due in expected.items():
        assert _rent(build_levels(state, {1: level}), 1) == due


def test_a_mortgaged_district_pays_nothing():
    state = replace(own(game(), 0, *BROWN), mortgaged=tuple(i == 1 for i in range(40)))
    assert _rent(state, 1) == 0
