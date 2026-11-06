"""The first player who ROTATES (D38 -> the rule, D46): with `rotate_first_player`, round r starts at seat
(r - 1) mod n -- everyone still plays once per round, and nobody starts with less than the others. The amount itself
is pinned in `test_rules_amounts.py`; here both settings are tested, so the mechanics hold whatever the rule says."""

from dataclasses import replace

from traveler_quartet.match.runner import play_game_rounds
from traveler_quartet.players.bots import BOTS
from traveler_quartet.rules.engine import new_game
from traveler_quartet.rules.turns import end_turn


def _game(rotate, players=4, rounds=30):
    state = new_game(seed=1, player_count=players)
    return replace(state, economy=replace(state.economy, rotate_first_player=rotate, rounds=rounds))


def _turns(state, count):
    seen = []
    for _ in range(count):
        state = end_turn(state)
        seen.append((state.round, state.current))
    return seen


def test_without_rotation_every_round_starts_at_seat_0():
    assert _turns(_game(0), 7) == [(1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3)]


def test_with_rotation_each_round_starts_one_seat_later():
    assert _turns(_game(1), 11) == [(1, 1), (1, 2), (1, 3),
                                     (2, 1), (2, 2), (2, 3), (2, 0),
                                     (3, 2), (3, 3), (3, 0), (3, 1)]


def test_with_rotation_an_eliminated_player_is_skipped_and_the_round_still_closes():
    state = _game(1)
    players = list(state.players)
    players[1] = replace(players[1], out=True)
    state = replace(state, players=tuple(players))
    assert _turns(state, 6) == [(1, 2), (1, 3), (2, 2), (2, 3), (2, 0), (3, 2)]


def test_with_rotation_the_game_still_ends_after_the_last_round():
    state = replace(_game(1, rounds=2), round=2, current=0)
    assert end_turn(state).pending == "over"


def test_a_whole_game_with_rotation_starts_each_round_at_its_seat():
    final, timed = play_game_rounds(_game(1, rounds=8), [BOTS["normal"]] * 4)
    first_roll = {}
    for round_, event in timed:
        if event.kind == "rolled":
            first_roll.setdefault(round_, event.player)
    assert first_roll == {r: (r - 1) % 4 for r in range(1, final.round + 1)}
