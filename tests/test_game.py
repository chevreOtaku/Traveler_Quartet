from traveler_quartet.match.runner import play_game
from traveler_quartet.rules.board import load_board
from traveler_quartet.rules.engine import new_game


def buy_everything(state, legal):
    return "buy" if "buy" in legal else legal[0]


def never_buy(state, legal):
    return "pass" if "pass" in legal else legal[0]


def _play(seed: int, chooser=buy_everything):
    return play_game(new_game(seed=seed, player_count=4), [chooser] * 4)


def test_a_game_ends_after_thirty_rounds():
    final, _ = _play(seed=11)
    assert final.over
    assert final.round == 30


def test_the_same_seed_replays_the_same_game():
    assert _play(seed=11) == _play(seed=11)


def test_another_seed_plays_another_game():
    assert _play(seed=11)[1] != _play(seed=12)[1]


def test_no_gold_appears_or_vanishes():
    final, events = _play(seed=11)
    with_the_bank = sum(dict(e.data).get("bank", 0) for e in events)
    assert sum(p.cash for p in final.players) + final.jackpot == 4 * 750 + with_the_bank


def test_the_bank_column_matches_the_purchases():
    final, events = _play(seed=11)
    board = load_board()
    bought = sum(board.squares[i].price for i, owner in enumerate(final.owners) if owner is not None)
    assert -sum(dict(e.data)["bank"] for e in events if e.kind == "bought") == bought


def test_nobody_buys_when_nobody_wants_to():
    final, _ = _play(seed=11, chooser=never_buy)
    assert all(owner is None for owner in final.owners)
