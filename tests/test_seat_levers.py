"""The advance of the first seat (D38). Gold for the later seats (`seat_bonus_cash`: seat k gets k x X more at the
start) is kept at 0 -- it corrects the advance but would FEEL unfair; it stays for a handicap mode. (A start further on
was measured and REMOVED: not monotonic, no effect on new seeds.) And a simulation must apply its amounts BEFORE the
players are seated, or a starting amount is silently ignored."""

import json

import pytest

from traveler_quartet.match.tournament import starting_state
from traveler_quartet.rules.board import DATA_DIR
from traveler_quartet.rules.engine import new_game


def test_the_rules_keep_the_gold_lever_at_zero():
    raw = json.loads((DATA_DIR / "economy.json").read_text(encoding="utf-8"))
    assert raw["seat_bonus_cash"] == 0 and "seat_start_offset" not in raw


def test_at_zero_every_seat_starts_alike():
    state = new_game(seed=1, player_count=4)
    assert {(p.cash, p.position) for p in state.players} == {(state.economy.start_cash, 0)}


def test_a_simulated_starting_amount_reaches_the_players():
    state = starting_state(seed=1, player_count=4, changes={"start_cash": 900})
    assert [p.cash for p in state.players] == [900] * 4


def test_gold_for_the_later_seats_grows_with_the_seat():
    state = starting_state(seed=1, player_count=4, changes={"seat_bonus_cash": 50})
    start = state.economy.start_cash
    assert [p.cash for p in state.players] == [start, start + 50, start + 100, start + 150]


def test_a_simulation_still_refuses_an_unknown_amount():
    with pytest.raises(ValueError, match="unknown amounts"):
        starting_state(seed=1, player_count=4, changes={"seat_bonus": 50})


def test_a_simulated_length_and_no_disasters_still_apply():
    state = starting_state(seed=1, player_count=4, disasters=False, rounds=10)
    cards = [card for _, deck in state.decks for card in deck]
    assert state.economy.rounds == 10 and all(state.catalog[c]["effect"] != "disaster" for c in cards)
