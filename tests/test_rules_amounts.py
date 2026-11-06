"""The AMOUNTS of the rules, pinned: a change of an amount is a decision, written in `decisions.md` and seen here --
never a side effect. The mechanics are tested elsewhere with simple numbers (`factory.MECHANICS_RENT_PERCENT`)."""

from traveler_quartet.rules.economy import load_economy


def test_the_rent_is_fifteen_percent_of_the_price_d43():
    assert load_economy().rent_percent == 15


def test_a_game_lasts_thirty_rounds_d40():
    assert load_economy().rounds == 30
