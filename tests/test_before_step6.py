"""What has to hold before the tournament of step 6: seats that rotate, a credible Easy player, a switch without
disasters, a richer report -- and a rules page that names every mechanism of the engine."""

from pathlib import Path

from factory import BROWN, cash, game, own
from test_specials import _landing_on
from traveler_quartet.match.tournament import run_tournament, seating
from traveler_quartet.players.bots import easy
from traveler_quartet.rules.engine import apply, legal_actions

RULES = Path(__file__).resolve().parents[1] / "RULES.md"


def test_the_seats_rotate_so_each_entrant_sits_everywhere_as_often():
    seats = ("normal", "easy", "easy", "easy")
    places = [seating(seats, game_number).index(0) for game_number in range(8)]
    assert sorted(places) == [0, 0, 1, 1, 2, 2, 3, 3]


def test_the_report_counts_wins_by_entrant_as_well_as_by_seat():
    report = run_tournament(games=8, first_seed=1, seats=("normal", "easy", "easy", "easy"))
    assert sum(report["wins_by_entrant"]) == 8 and sum(report["wins_by_seat"]) == 8


def test_the_easy_player_buys_whenever_it_can_pay():
    state = cash(_landing_on(8, start=0), 0, 60)
    state, _ = apply(state, "roll")
    assert easy(state, legal_actions(state)) == "buy"


def test_the_easy_player_bids_up_to_half_the_price_then_drops():
    state, _ = apply(_landing_on(8, start=0), "roll")
    state, _ = apply(state, "pass")
    assert easy(state, legal_actions(state)) == "raise:5"
    from dataclasses import replace
    state = replace(state, auction=replace(state.auction, price=25))
    assert easy(state, legal_actions(state)) == "drop"


def test_the_easy_player_never_trades():
    state = own(own(game(players=2), 0, 1), 1, 3)
    state, _ = apply(state, "offer:1:40:::0:3:")
    assert easy(state, legal_actions(state)) == "refuse"


def test_without_disasters_no_disaster_happens():
    report = run_tournament(games=30, first_seed=1, seats=("normal",) * 4, disasters=False)
    assert report["disasters_per_game_mean"] == 0


def test_the_report_counts_the_social_moves():
    report = run_tournament(games=30, first_seed=1, seats=("normal",) * 4)
    for key in ("trades_per_game_mean", "auctions_per_game_mean", "curses_per_game_mean", "disasters_per_game_mean",
                "dungeon_stays_per_game_mean", "shared_stalls_per_game_mean"):
        assert key in report


def test_the_public_rules_page_names_every_mechanism_of_the_engine():
    text = RULES.read_text(encoding="utf-8").lower()
    for word in ("auction", "sealed", "mirror", "negotiation", "portal", "dungeon", "shared stall", "curse",
                 "pair", "jackpot", "mortgage", "trading", "disaster", "crises", "double"):
        assert word in text, f"RULES.md does not mention {word!r} (E15)"


def test_each_win_goes_to_the_entrant_who_really_sat_at_the_winning_seat():
    seats = ("normal", "easy", "easy", "easy")
    report = run_tournament(games=12, first_seed=1, seats=seats)
    for n, (seat, entrant) in enumerate(report["winners"]):
        assert entrant == seating(seats, n)[seat]
    assert report["wins_by_entrant"] == [sum(1 for _, e in report["winners"] if e == k) for k in range(4)]
