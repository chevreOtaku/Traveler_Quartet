"""The Hard computer CALCULATES (decisions D39): where pawns land, what completes its town or a rival's, what a house
earns per gold spent, who really leads. Each test is a choice where the Normal computer plays differently."""

from dataclasses import replace

from factory import BROWN, ORANGE, build_levels, cash, game, own
from test_specials import _landing_on
from traveler_quartet.match.runner import play_game
from traveler_quartet.match.tournament import run_tournament
from traveler_quartet.players.bots import normal
from traveler_quartet.players.hard import hard
from traveler_quartet.players.landing import landing_frequencies
from traveler_quartet.rules.engine import apply, legal_actions, new_game

DUNGEON, GO_TO_DUNGEON = 10, 30
GREEN = (31, 32, 34)


def _choices(state):
    legal = legal_actions(state)
    return hard(state, legal), normal(state, legal)


def test_landing_frequencies_add_up_to_one_and_nobody_stays_on_go_to_dungeon():
    frequencies = landing_frequencies(game().board)
    assert abs(sum(frequencies) - 1) < 1e-9
    assert frequencies[GO_TO_DUNGEON] == 0 and frequencies[DUNGEON] == max(frequencies)


def test_the_hard_computer_finishes_whole_games_and_is_reproducible():
    first = play_game(new_game(seed=7, player_count=4), [hard] * 4)
    assert first[0].over and first == play_game(new_game(seed=7, player_count=4), [hard] * 4)


def test_it_buys_the_district_that_completes_its_town_even_below_the_normal_reserve():
    state, _ = apply(cash(own(_landing_on(3, start=0), 0, 1), 0, 60), "roll")
    assert _choices(state) == ("buy", "pass")


def test_it_bids_above_the_price_for_the_district_that_completes_its_town():
    state, _ = apply(own(_landing_on(3, start=0), 0, 1), "roll")
    state, _ = apply(state, "pass")
    state = replace(state, auction=replace(state.auction, price=30))
    hard_choice, normal_choice = _choices(state)
    assert hard_choice.startswith("raise:") and normal_choice == "drop"


def test_it_refuses_a_good_price_for_the_district_that_completes_the_rival_town():
    state, _ = apply(own(own(game(players=2), 0, 1), 1, 3), "offer:1:40:::0:3:")
    assert _choices(state) == ("refuse", "accept")


def test_it_accepts_a_good_price_when_the_district_completes_nothing():
    state, _ = apply(own(game(players=2), 1, 6), "offer:1:70:::0:6:")
    assert hard(state, legal_actions(state)) == "accept"


def _in_dungeon(state, round_):
    me = replace(state.players[0], position=DUNGEON, dungeon_turns=2)
    return replace(state, players=(me,) + state.players[1:], round=round_)


def test_it_pays_to_leave_the_dungeon_early_while_districts_are_free():
    assert hard(_in_dungeon(game(), 2), legal_actions(_in_dungeon(game(), 2))) == "pay_exit"


def test_it_stays_in_the_dungeon_late_when_every_district_is_owned():
    districts = [i for i, s in enumerate(game().board.squares) if s.kind == "district"]
    state = _in_dungeon(own(game(), 1, *districts), 25)
    assert "pay_exit" in legal_actions(state) and hard(state, legal_actions(state)) == "roll"


def test_it_curses_the_player_who_is_richest_in_net_worth_not_in_cash():
    state = own(cash(cash(game(players=3), 1, 600), 2, 500), 2, *GREEN)
    me = replace(state.players[0], cards=("curse",))
    state = replace(state, players=(me,) + state.players[1:])
    assert _choices(state) == ("curse:2", "curse:1")


def test_it_builds_first_where_a_house_earns_the_most_per_gold():
    state = own(game(), 0, *BROWN, *ORANGE)
    hard_choice, normal_choice = _choices(state)
    assert int(hard_choice.split(":")[1]) in ORANGE and int(normal_choice.split(":")[1]) in BROWN


def test_it_lifts_a_mortgage_when_it_is_rich():
    state = own(game(), 0, 6)
    state = replace(state, mortgaged=tuple(i == 6 for i in range(len(state.owners))))
    assert _choices(state) == ("unmortgage:6", "roll")


def test_it_offers_to_buy_the_last_district_of_its_town():
    state = own(own(game(players=2), 0, 16, 18), 1, 19)
    choice = hard(state, legal_actions(state))
    assert choice.startswith("offer:1:") and choice.endswith(":19:")


def test_it_keeps_building_while_the_danger_on_the_board_allows():
    state = build_levels(own(cash(game(players=2), 0, 200), 0, *ORANGE), {16: 1, 18: 1, 19: 1})
    state = build_levels(own(state, 1, *GREEN), {31: 3, 32: 3, 34: 3})
    assert hard(state, legal_actions(state)) == "roll"


def test_the_tournament_can_seat_the_hard_computer():
    report = run_tournament(games=4, first_seed=1, seats=("hard", "easy", "easy", "easy"))
    assert sum(report["wins_by_entrant"]) == 4


def test_it_stays_in_the_dungeon_late_even_when_districts_are_still_free():
    state = _in_dungeon(game(), 25)
    assert "pay_exit" in legal_actions(state) and hard(state, legal_actions(state)) == "roll"
