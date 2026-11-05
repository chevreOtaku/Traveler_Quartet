from factory import BROWN, ORANGE, at, build_levels, game, own
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.engine import apply


def _passing_start(state):
    steps = sum(roll(state.seed, 0))
    return at(state, 0, 40 - steps + 1 if steps > 1 else 39)


def _income(state):
    after, events = apply(_passing_start(state), "roll")
    return next(dict(e.data)["amount"] for e in events if e.kind == "passed_start")


def test_the_bare_salary_is_one_hundred():
    assert _income(game()) == 100


def test_a_whole_pair_adds_ten():
    assert _income(own(game(), 0, *BROWN, *ORANGE)) == 110


def test_one_town_of_a_pair_adds_nothing():
    assert _income(own(game(), 0, *BROWN)) == 100


def test_each_own_stall_adds_twenty():
    state = build_levels(own(game(), 0, *BROWN), {1: 4, 3: 4})
    assert _income(state) == 140
