"""Whole-game regression checks with fixed seeds and mixed computer players.

Run with: python -m pytest tests/test_match_regression.py -v
"""

import pytest

from traveler_quartet.match.runner import play_game_rounds
from traveler_quartet.players.bots import easy, normal
from traveler_quartet.rules.engine import legal_actions, new_game


@pytest.fixture(params=[2, 3, 4], ids=lambda count: f"{count}-players")
def player_count(request):
    return request.param


@pytest.fixture(params=[1, 11, 42], ids=lambda seed: f"seed-{seed}")
def completed_match(request, player_count):
    initial = new_game(seed=request.param, player_count=player_count)
    choosers = tuple((easy, normal)[seat % 2] for seat in range(player_count))
    final, timed_events = play_game_rounds(initial, choosers)
    return initial, choosers, final, timed_events


def test_mixed_players_finish_within_the_round_limit(completed_match):
    initial, _, final, timed_events = completed_match

    assert final.over
    assert 1 <= final.round <= initial.economy.rounds
    assert legal_actions(final) == ()
    assert timed_events, "A complete game must record events"
    rounds = [round_number for round_number, _ in timed_events]
    assert rounds == sorted(rounds)
    assert rounds[0] == 1
    assert rounds[-1] <= final.round


def test_mixed_players_replay_the_same_actions_and_events(completed_match):
    initial, choosers, final, timed_events = completed_match

    replay_final, replay_events = play_game_rounds(initial, choosers)

    assert replay_final == final
    assert replay_events == timed_events
    assert initial == new_game(seed=initial.seed, player_count=len(initial.players))


def test_every_gold_change_is_accounted_for_by_the_bank(completed_match):
    initial, _, final, timed_events = completed_match
    starting_gold = sum(player.cash for player in initial.players) + initial.jackpot
    bank_flow = sum(dict(event.data).get("bank", 0) for _, event in timed_events)
    remaining_gold = sum(player.cash for player in final.players) + final.jackpot

    assert remaining_gold == starting_gold + bank_flow
