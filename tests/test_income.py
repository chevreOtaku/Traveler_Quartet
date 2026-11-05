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


def test_each_whole_town_earns_its_bonus_at_start_and_the_rule_says_zero():
    from dataclasses import replace as _replace
    from factory import BROWN, ORANGE, own
    from traveler_quartet.rules.income import start_income
    state = own(game(), 0, *BROWN, *ORANGE)
    assert state.economy.town_bonus == 0
    rich = _replace(state, economy=_replace(state.economy, town_bonus=10, pair_bonus=30))
    salary = state.economy.salary
    assert start_income(rich, 0) == salary + 2 * 10 + 30
    assert start_income(own(rich, 0, *BROWN), 1) == salary
