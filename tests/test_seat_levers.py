"""The advance of the first seat (D38): two levers to measure, both 0 in the rules -- gold for the later seats
(`seat_bonus_cash`: seat k gets k x X more at the start) and a start further on (`seat_start_offset`: seat k starts
k x N squares on). And a simulation must apply its amounts BEFORE the players are seated, or a starting amount is
silently ignored."""

import json

import pytest

from traveler_quartet.match.tournament import starting_state
from traveler_quartet.rules.board import DATA_DIR
from traveler_quartet.rules.engine import new_game


def test_the_rules_keep_both_levers_at_zero():
    raw = json.loads((DATA_DIR / "economy.json").read_text(encoding="utf-8"))
    assert raw["seat_bonus_cash"] == 0 and raw["seat_start_offset"] == 0


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


def test_a_start_further_on_grows_with_the_seat_and_lands_nowhere():
    state = starting_state(seed=1, player_count=4, changes={"seat_start_offset": 2})
    assert [p.position for p in state.players] == [0, 2, 4, 6]
    assert all(owner is None for owner in state.owners) and state.round == 1


def test_a_simulation_still_refuses_an_unknown_amount():
    with pytest.raises(ValueError, match="unknown amounts"):
        starting_state(seed=1, player_count=4, changes={"seat_bonus": 50})


def test_a_simulated_length_and_no_disasters_still_apply():
    state = starting_state(seed=1, player_count=4, disasters=False, rounds=10)
    cards = [card for _, deck in state.decks for card in deck]
    assert state.economy.rounds == 10 and all(state.catalog[c]["effect"] != "disaster" for c in cards)
