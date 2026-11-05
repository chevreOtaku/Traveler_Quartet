import subprocess
import sys

from traveler_quartet.match.runner import play_game, play_game_rounds
from traveler_quartet.match.tournament import run_tournament
from traveler_quartet.players.bots import normal
from traveler_quartet.rules.engine import new_game


def test_rounds_are_recorded_with_each_event():
    final, timed = play_game_rounds(new_game(seed=2, player_count=4), [normal] * 4)
    assert timed[0][0] == 1
    assert timed[-1][0] <= 30
    assert final == play_game(new_game(seed=2, player_count=4), [normal] * 4)[0]


def test_a_tournament_reports_the_first_house_and_is_reproducible():
    report = run_tournament(games=20, first_seed=1, seats=("normal",) * 4)
    assert report == run_tournament(games=20, first_seed=1, seats=("normal",) * 4)
    assert report["games"] == 20
    assert 1 <= report["first_house_round_median"] <= 31
    assert 0.0 <= report["games_with_a_house"] <= 1.0
    assert sum(report["wins_by_seat"]) == 20


def test_the_command_runs_a_small_tournament():
    result = subprocess.run([sys.executable, "-m", "traveler_quartet", "tournament", "--games", "5"],
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert "first_house_round_median" in result.stdout


def test_a_player_may_say_something_with_any_action_and_it_is_recorded_beside_it():
    def talkative(state, legal):
        action = normal(state, legal)
        return action, f"I choose {action.split(':')[0]}"
    final, events = play_game(new_game(seed=2, player_count=2), [talkative, normal])
    said = [e for e in events if e.kind == "said"]
    assert said and all(dict(e.data)["text"].startswith("I choose") for e in said)
    assert all(e.player == 0 for e in said)


def test_saying_nothing_records_nothing():
    _, events = play_game(new_game(seed=2, player_count=2), [normal, normal])
    assert not any(e.kind == "said" for e in events)


def test_a_game_that_never_ends_stops_with_a_clear_error():
    import pytest
    with pytest.raises(RuntimeError, match="steps"):
        play_game_rounds(new_game(seed=2, player_count=2), [normal, normal], max_steps=10)
