from dataclasses import replace
from typing import Callable, List, Tuple

from factory import at, cash, game, own
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.engine import apply, legal_actions

PORTALS = (5, 15, 25, 35)
UTILITIES = (12, 28)


def _seed(want: Callable[[List[Tuple[int, int]]], bool], rolls: int = 1) -> int:
    return next(s for s in range(20000) if want([roll(s, n) for n in range(rolls)]))


def _single(total: int) -> int:
    return _seed(lambda r: sum(r[0]) == total and r[0][0] != r[0][1])


def _landing_on(square: int, start: int = 0):
    steps = (square - start) % 40
    assert 3 <= steps <= 11, f"two different dice make 3 to 11, not {steps} (E9, E10)"
    seed = _seed(lambda r: (start + sum(r[0])) % 40 == square and r[0][0] != r[0][1])
    return at(game(seed=seed), 0, start)


def test_a_portal_is_bought_at_its_price():
    state, _ = apply(_landing_on(5), "roll")
    assert legal_actions(state) == ("buy", "pass")
    state, _ = apply(state, "buy")
    assert state.owners[5] == 0 and state.players[0].cash == 750 - 100


def test_a_portal_rent_is_fifteen_and_fifty_with_all_four():
    one, _ = apply(own(_landing_on(5), 1, 5), "roll")
    assert one.players[0].cash == 750 - 15
    four, _ = apply(own(_landing_on(5), 1, *PORTALS), "roll")
    assert four.players[0].cash == 750 - 50


def test_after_a_portal_the_player_may_jump_to_the_next_one_and_nothing_happens_there():
    state, _ = apply(own(own(_landing_on(5), 1, 5), 1, 15), "roll")
    assert set(legal_actions(state)) == {"jump", "stay"}
    state, events = apply(state, "jump")
    assert state.players[0].position == 15
    assert state.players[0].cash == 750 - 15
    assert not state.players[0].jump_ready
    assert events[0].kind == "jumped"


def test_staying_keeps_the_jump_for_later():
    state, _ = apply(own(_landing_on(5), 1, 5), "roll")
    state, _ = apply(state, "stay")
    assert state.players[0].jump_ready


def test_no_jump_question_without_the_right():
    state = own(_landing_on(5), 1, 5)
    state = replace(state, players=(replace(state.players[0], jump_ready=False),) + state.players[1:])
    state, _ = apply(state, "roll")
    assert "jump" not in legal_actions(state)


def test_passing_start_gives_the_jump_back():
    state = _landing_on(3, start=35)
    state = replace(state, players=(replace(state.players[0], jump_ready=False),) + state.players[1:])
    state, _ = apply(state, "roll")
    assert state.players[0].jump_ready


def test_a_jump_across_start_pays_the_salary_but_uses_both_laps():
    state, _ = apply(own(_landing_on(35, start=30), 1, 35), "roll")
    state, _ = apply(state, "jump")
    assert state.players[0].position == 5
    assert state.players[0].cash == 750 - 15 + 100
    assert not state.players[0].jump_ready


def test_a_utility_rent_is_the_dice_times_two_or_five_with_both():
    one, _ = apply(own(_landing_on(12, start=5), 1, 12), "roll")
    assert one.players[0].cash == 750 - 7 * 2
    both, _ = apply(own(_landing_on(12, start=5), 1, *UTILITIES), "roll")
    assert both.players[0].cash == 750 - 7 * 5


def test_a_tax_fills_the_jackpot():
    state, _ = apply(_landing_on(17, start=10), "roll")
    assert state.players[0].cash == 750 - 50 and state.jackpot == 50


def test_the_park_pays_the_whole_jackpot():
    state = replace(_landing_on(20, start=10), jackpot=125)
    state, _ = apply(state, "roll")
    assert state.players[0].cash == 750 + 125 and state.jackpot == 0


def test_a_tax_bigger_than_the_cash_is_a_debt_paid_into_the_jackpot():
    state = own(cash(_landing_on(33, start=30), 0, 10), 0, 37)
    state, _ = apply(state, "roll")
    assert state.pending == "debt"
    state, _ = apply(state, "mortgage:37")
    assert state.jackpot == 75 and state.players[0].cash == 10 + 87 - 75


def test_the_go_to_dungeon_square_sends_to_the_dungeon_without_salary():
    state, _ = apply(_landing_on(30, start=25), "roll")
    assert state.players[0].position == 10
    assert state.players[0].dungeon_turns == 2
    assert state.players[0].cash == 750


def _in_dungeon(seed: int):
    state = at(game(seed=seed), 0, 10)
    return replace(state, players=(replace(state.players[0], dungeon_turns=2),) + state.players[1:])


def test_in_the_dungeon_one_rolls_or_pays_to_leave():
    state = _in_dungeon(_single(5))
    assert {"roll", "pay_exit"} <= set(legal_actions(state))


def test_paying_to_leave_costs_twenty_five_then_the_turn_goes_on():
    state, _ = apply(_in_dungeon(_single(5)), "pay_exit")
    assert state.players[0].cash == 750 - 25 and state.players[0].dungeon_turns == 0
    assert legal_actions(state)[0] == "roll"


def test_a_roll_without_double_keeps_the_player_inside_for_one_round_less():
    state, _ = apply(_in_dungeon(_single(5)), "roll")
    assert state.players[0].position == 10 and state.players[0].dungeon_turns == 1
    assert state.current == 1


def test_a_double_frees_the_player_and_moves_him():
    seed = _seed(lambda r: r[0] == (3, 3))
    state, _ = apply(_in_dungeon(seed), "roll")
    assert state.players[0].dungeon_turns == 0 and state.players[0].position == 16


def _answer_the_landing(state):
    answers = {"buy": "pass", "jump": "stay", "auction": "drop"}
    while state.current == 0 and state.pending in answers:
        state, _ = apply(state, answers[state.pending])
    return state


def test_a_double_outside_the_dungeon_plays_again():
    seed = _seed(lambda r: r[0][0] == r[0][1] and r[1][0] != r[1][1], rolls=2)
    state = game(seed=seed)
    state, _ = apply(state, "roll")
    state = _answer_the_landing(state)
    assert state.current == 0 and legal_actions(state)[0] == "roll"


def test_three_doubles_in_a_row_send_to_the_dungeon():
    seed = _seed(lambda r: all(a == b for a, b in r), rolls=3)
    state = game(seed=seed)
    for _ in range(3):
        state, _ = apply(state, "roll")
        state = _answer_the_landing(state)
    assert state.players[0].position == 10 and state.players[0].dungeon_turns == 2


def test_a_portal_and_a_utility_can_be_mortgaged_for_half_their_price():
    state = own(game(), 0, 5, 12)
    assert {"mortgage:5", "mortgage:12"} <= set(legal_actions(state))
    state, _ = apply(state, "mortgage:5")
    assert state.players[0].cash == 750 + 50
