from dataclasses import replace

from factory import BROWN, at, build_levels, cash, game, own
from test_cards import CHANCE, EVENT, _drawing, _seed
from traveler_quartet.players.bots import normal
from traveler_quartet.rules.card_effects import EFFECTS
from traveler_quartet.rules.engine import apply, legal_actions, new_game


def test_the_goddess_takes_ten_from_you_and_gives_ten_to_each_other():
    state, _ = apply(_drawing("goddess_blessing", CHANCE, 0, players=3), "roll")
    assert [p.cash for p in state.players] == [740, 760, 760]


def test_the_dungeon_card_sends_you_there():
    state, _ = apply(_drawing("to_dungeon", CHANCE, 0), "roll")
    assert state.players[0].position == 10 and state.players[0].dungeon_turns == 2


def test_the_festival_pays_each_owner_in_the_town():
    state = own(own(_drawing("festival", EVENT, 0, players=3), 1, 1), 2, 3)
    state, _ = apply(state, "roll")
    assert state.players[1].cash == 770 and state.players[2].cash == 770


def test_the_cabbages_cost_a_repair_to_a_town_with_buildings():
    from traveler_quartet.rules.cards import carousel
    seed = next(s for s in range(500) if carousel(game(seed=s)) == "brown")
    state = build_levels(own(game(seed=seed), 1, *BROWN), {1: 1})
    result, events, _ = EFFECTS["repair"](state, state.catalog["cabbages"])
    assert next(dict(e.data)["town"] for e in events if e.kind == "card") == "brown"
    assert result.players[1].cash == 750 - 25 * 50 // 100
    assert result.buildings[1] == 1


def _dungeon_with(card: str, double: bool = False):
    seed = _seed(lambda r: (r[0][0] == r[0][1]) == double)
    state = at(new_game(seed=seed, player_count=2), 0, 10)
    state = replace(state, players=(replace(state.players[0], dungeon_turns=2),) + state.players[1:])
    return replace(state, decks=tuple((d, (card,) + tuple(c for c in o if c != card)) if d == "adventurer"
                                      else (d, o) for d, o in state.decks))


def test_the_saint_costs_the_turn_then_frees():
    state, _ = apply(_dungeon_with("saint"), "roll")
    assert state.players[0].dungeon_turns == 0 and state.players[0].position == 10 and state.current == 1


def test_finding_the_exit_frees_and_the_roll_moves_on():
    state, _ = apply(_dungeon_with("exit"), "roll")
    assert state.players[0].dungeon_turns == 0 and state.players[0].position != 10


def test_being_lost_forbids_leaving_early_even_on_a_double():
    state, _ = apply(_dungeon_with("lost", double=True), "roll")
    assert state.players[0].position == 10 and state.players[0].dungeon_turns == 1
    assert state.players[0].dungeon_locked


def test_a_locked_player_cannot_pay_to_leave():
    state = _dungeon_with("lost")
    state = replace(state, players=(replace(state.players[0], dungeon_locked=True),) + state.players[1:])
    assert "pay_exit" not in legal_actions(state)


def test_hanging_out_with_adventurers_draws_an_event():
    state, events = apply(_dungeon_with("adventurers"), "roll")
    drawn = [dict(e.data)["card"] for e in events if e.kind == "card"]
    assert drawn[0] == "adventurers" and len(drawn) >= 2 and state.catalog[drawn[1]]["deck"] == "event"


def test_the_normal_computer_curses_the_richest_rival():
    state, _ = apply(_drawing("curse", EVENT, 0, players=3, die_even=False), "roll")
    state = cash(cash(state, 1, 300), 2, 900)
    assert normal(state, legal_actions(state)) == "curse:2"
