from dataclasses import replace

import pytest

from traveler_quartet.rules.board import load_board
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.economy import load_economy
from traveler_quartet.rules.engine import IllegalAction, apply, legal_actions, new_game

BOARD = load_board()
ECONOMY = load_economy()


def _seed_whose_first_roll_lands_on(kind: str) -> int:
    for seed in range(1000):
        if BOARD.squares[sum(roll(seed, 0))].kind == kind:
            return seed
    raise AssertionError(f"no seed lands on {kind}")


def test_a_new_game_starts_everyone_at_start_with_the_starting_cash():
    state = new_game(seed=1, player_count=4)
    assert [p.position for p in state.players] == [0, 0, 0, 0]
    assert [p.cash for p in state.players] == [750] * 4
    assert [a for a in legal_actions(state) if not a.startswith("offer:")] == ["roll"]


def test_an_action_that_is_not_legal_is_refused():
    with pytest.raises(IllegalAction):
        apply(new_game(seed=1, player_count=2), "buy")


def test_landing_on_a_free_district_asks_to_buy_or_pass():
    state, _ = apply(new_game(seed=_seed_whose_first_roll_lands_on("district"), player_count=2), "roll")
    assert legal_actions(state) == ("buy", "pass")


def test_a_player_who_cannot_afford_the_district_is_not_offered_it():
    state = new_game(seed=_seed_whose_first_roll_lands_on("district"), player_count=2)
    broke = replace(state.players[0], cash=1)
    state = replace(state, players=(broke,) + state.players[1:])
    state, _ = apply(state, "roll")
    assert "buy" not in legal_actions(state)
    assert state.pending == "auction"


def test_buying_takes_the_price_and_hands_the_turn_on():
    state, _ = apply(new_game(seed=_seed_whose_first_roll_lands_on("district"), player_count=2), "roll")
    square = state.players[0].position
    state, events = apply(state, "buy")
    assert state.owners[square] == 0
    assert state.players[0].cash == 750 - BOARD.squares[square].price
    assert state.current == 1
    assert [a for a in legal_actions(state) if not a.startswith("offer:")] == ["roll"]
    assert events[0].kind == "bought"


def test_landing_on_a_rival_district_pays_the_rent_to_its_owner():
    seed = _seed_whose_first_roll_lands_on("district")
    square = sum(roll(seed, 0))
    owners = tuple(1 if i == square else None for i in range(40))
    state = replace(new_game(seed=seed, player_count=2), owners=owners)
    state, events = apply(state, "roll")
    due = BOARD.squares[square].price * ECONOMY.rent_percent // 100
    assert state.players[0].cash == 750 - due
    assert state.players[1].cash == 750 + due
    assert any(e.kind == "rent_paid" for e in events)
    assert state.current == 1
