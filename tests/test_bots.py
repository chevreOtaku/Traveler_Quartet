from factory import BROWN, cash, game, own
from traveler_quartet.match.runner import play_game
from traveler_quartet.players.bots import easy, normal
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.engine import apply, legal_actions, new_game


def _seed_landing_on(square: int) -> int:
    return next(s for s in range(2000) if sum(roll(s, 0)) == square)


def test_both_computers_finish_whole_games_with_legal_moves_only():
    for chooser in (easy, normal):
        final, _ = play_game(new_game(seed=3, player_count=4), [chooser] * 4)
        assert final.over


def test_the_easy_computer_is_reproducible():
    first = play_game(new_game(seed=5, player_count=4), [easy] * 4)
    assert first == play_game(new_game(seed=5, player_count=4), [easy] * 4)


def test_the_normal_computer_keeps_a_reserve_before_buying():
    state = cash(game(seed=_seed_landing_on(3)), 0, 120)
    state, _ = apply(state, "roll")
    assert normal(state, legal_actions(state)) == "pass"


def test_the_normal_computer_buys_when_it_can_keep_its_reserve():
    state, _ = apply(game(seed=_seed_landing_on(3)), "roll")
    assert normal(state, legal_actions(state)) == "buy"


def test_the_normal_computer_builds_on_a_whole_town_before_rolling():
    state = own(game(), 0, *BROWN)
    assert normal(state, legal_actions(state)).startswith("build:")


def test_the_normal_computer_rolls_when_building_would_break_its_reserve():
    state = cash(own(game(), 0, *BROWN), 0, 110)
    assert normal(state, legal_actions(state)) == "roll"
