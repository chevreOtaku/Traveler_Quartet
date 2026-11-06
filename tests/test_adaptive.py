"""The Adaptive computer READS the economy (decision D42): it buys, builds and bids by the numbers of the rules -- the rent
it can still collect before the end, what a district or a house will count for at the end -- so it changes its mind
when the rules change, where the Hard computer keeps playing for the rules it was written for."""

from dataclasses import replace

from factory import ORANGE, game, own
from test_specials import _landing_on
from traveler_quartet.match.runner import play_game
from traveler_quartet.match.tournament import run_tournament
from traveler_quartet.players.adaptive import adaptive
from traveler_quartet.players.economics import buy_gain, house_gain, rounds_left
from traveler_quartet.players.hard import hard
from traveler_quartet.rules.engine import apply, legal_actions, new_game


def _rules(state, round_=None, **changes):
    state = replace(state, economy=replace(state.economy, **changes))
    return replace(state, round=round_) if round_ is not None else state


def _landed(round_, **changes):
    state, _ = apply(_landing_on(3, start=0), "roll")
    return _rules(state, round_, **changes)


def _choices(state):
    legal = legal_actions(state)
    return adaptive(state, legal), hard(state, legal)


def test_it_finishes_whole_games_and_is_reproducible():
    first = play_game(new_game(seed=7, player_count=4), [adaptive] * 4)
    assert first[0].over and first == play_game(new_game(seed=7, player_count=4), [adaptive] * 4)


def test_the_rounds_left_shrink_to_nothing_at_the_end():
    state = game()
    assert rounds_left(replace(state, round=1)) > rounds_left(replace(state, round=20)) > 0
    assert rounds_left(replace(state, round=state.economy.rounds)) == 0


def test_early_in_the_game_it_buys_like_the_hard_computer():
    assert _choices(_landed(1)) == ("buy", "buy")


def test_late_when_a_district_counts_for_half_at_the_end_it_does_not_buy():
    state = _landed(29, final_value_percent=50)
    assert buy_gain(state, 3, 0) < 0 and _choices(state) == ("pass", "buy")


def test_late_when_a_district_counts_in_full_buying_still_costs_nothing():
    state = _landed(29)
    assert buy_gain(state, 3, 0) >= 0 and _choices(state)[0] == "buy"


def test_it_builds_early_where_three_rivals_will_pay_the_rent():
    state = _rules(own(game(players=4), 0, *ORANGE), 1, final_value_percent=50)
    assert house_gain(state, 16) > 0 and adaptive(state, legal_actions(state)).startswith("build:")


def test_it_stops_building_late_when_a_house_counts_for_half():
    state = _rules(own(game(players=4), 0, *ORANGE), 28, final_value_percent=50)
    assert house_gain(state, 16) < 0
    adaptive_choice, hard_choice = _choices(state)
    assert adaptive_choice == "roll" and hard_choice.startswith("build:")


def test_it_bids_less_for_a_district_worth_less_at_the_end():
    state, _ = apply(_landing_on(3, start=0), "roll")
    state, _ = apply(state, "pass")
    state = replace(state, auction=replace(state.auction, price=25))
    assert adaptive(_rules(state, 29), legal_actions(state)).startswith("raise:")
    assert adaptive(_rules(state, 29, final_value_percent=50), legal_actions(state)) == "drop"


def test_the_tournament_can_seat_it():
    report = run_tournament(games=2, first_seed=1, seats=("adaptive", "normal", "normal", "normal"))
    assert sum(report["wins_by_entrant"]) == 2


def test_three_rivals_land_three_times_as_often_as_one():
    from traveler_quartet.players.economics import expected_hits
    one, three = expected_hits(game(players=2), 16, 0), expected_hits(game(players=4), 16, 0)
    assert abs(three - 3 * one) < 1e-9


def test_a_double_rolls_again_so_a_turn_makes_43_36_moves_on_average():
    from traveler_quartet.players.economics import ROLLS_PER_TURN
    assert abs(ROLLS_PER_TURN - 43 / 36) < 1e-12


def test_the_district_that_completes_a_town_is_worth_more_than_the_same_one_alone():
    from traveler_quartet.players.economics import worth
    alone, completing = game(players=4), own(game(players=4), 0, 1)
    assert worth(completing, 3, 0) > worth(alone, 3, 0)


def test_completing_a_town_also_lifts_the_rent_of_its_other_districts():
    from traveler_quartet.players.economics import expected_hits, worth
    alone, completing = game(players=4), own(game(players=4), 0, 1)
    own_square_only = expected_hits(alone, 3, 0) * 3          # its own rent goes from 3 (bare) to 6 (whole town)
    assert worth(completing, 3, 0) - worth(alone, 3, 0) > own_square_only + 1e-9
