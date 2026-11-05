from dataclasses import replace

from factory import BROWN, at, build_levels, cash, game, own
from traveler_quartet.rules.cards import deck_of
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.engine import apply, legal_actions, new_game

CHANCE, EVENT = 7, 4
DARK_BLUE, LIGHT_BLUE = (37, 39), (6, 8, 9)
ORANGE = (16, 18, 19)


def _seed(want, rolls=1):
    return next(s for s in range(20000) if want([roll(s, n) for n in range(rolls)]))


def _drawing(card: str, square: int, start: int, players: int = 2, die_even=None):
    steps = (square - start) % 40
    assert 3 <= steps <= 11, "two different dice make 3 to 11 (E10)"

    def ok(r):
        first = (start + sum(r[0])) % 40 == square and r[0][0] != r[0][1]
        return first and (die_even is None or (r[1][0] % 2 == 0) == die_even)
    state = at(game(players=players, seed=_seed(ok, rolls=2)), 0, start)
    deck = deck_of(state, card)
    order = dict(state.decks)[deck]
    return replace(state, decks=tuple((d, (card,) + tuple(c for c in o if c != card)) if d == deck else (d, o)
                                      for d, o in state.decks))


def test_the_decks_are_shuffled_from_the_seed_and_hold_every_card():
    one, again, other = new_game(seed=1, player_count=2), new_game(seed=1, player_count=2), new_game(seed=2, player_count=2)
    assert one.decks == again.decks and one.decks != other.decks
    assert {d for d, _ in one.decks} == {"chance", "event", "adventurer"}


def test_a_drawn_card_goes_under_its_deck():
    state = _drawing("sword", CHANCE, 0)
    state, _ = apply(state, "roll")
    assert dict(state.decks)["chance"][-1] == "sword"


def test_a_gain_card_pays_from_the_bank():
    state, events = apply(_drawing("sword", CHANCE, 0), "roll")
    assert state.players[0].cash == 750 + 50
    assert any(e.kind == "card" for e in events)


def test_the_birthday_pays_every_player():
    state, _ = apply(_drawing("birthday", CHANCE, 0, players=3), "roll")
    assert [p.cash for p in state.players] == [850, 850, 850]


def test_a_card_that_does_nothing_does_nothing():
    state, _ = apply(_drawing("radish", CHANCE, 0), "roll")
    assert state.players[0].cash == 750


def test_the_slime_pays_on_an_even_die_and_takes_on_an_odd_one():
    even, _ = apply(_drawing("slime", CHANCE, 0, die_even=True), "roll")
    odd, _ = apply(_drawing("slime", CHANCE, 0, die_even=False), "roll")
    assert even.players[0].cash == 750 + 100 and odd.players[0].cash == 750 - 20


def test_the_lost_hero_collects_ten_from_each_other_player():
    state, _ = apply(_drawing("lost_hero", CHANCE, 0, players=3), "roll")
    assert [p.cash for p in state.players] == [770, 740, 740]


def test_the_cart_moves_back_three_squares_and_lands_there():
    state, _ = apply(_drawing("cart", CHANCE, 0), "roll")
    assert state.players[0].position == 4


def test_advance_to_start_pays_the_start_income():
    state, _ = apply(_drawing("to_start", CHANCE, 0), "roll")
    assert state.players[0].position == 0 and state.players[0].cash == 750 + 100


def test_the_tax_collector_takes_twenty_per_building():
    state = build_levels(own(_drawing("tax_collector", CHANCE, 0), 0, *BROWN), {1: 2, 3: 4})
    state, _ = apply(state, "roll")
    assert state.players[0].cash == 750 - 20 * 3


def test_the_rope_is_kept_and_frees_from_the_dungeon():
    state, _ = apply(_drawing("rope", CHANCE, 0), "roll")
    assert "rope" in state.players[0].cards
    state = at(replace(state, current=0, pending="roll", doubles=0), 0, 10)
    state = replace(state, players=(replace(state.players[0], dungeon_turns=2),) + state.players[1:])
    assert "use_rope" in legal_actions(state)
    state, _ = apply(state, "use_rope")
    assert state.players[0].dungeon_turns == 0 and "rope" not in state.players[0].cards


def test_the_first_invention_is_discovered_then_it_becomes_a_wave_of_demand():
    state = own(_drawing("mayonnaise", EVENT, 0), 1, *BROWN)
    state, events = apply(state, "roll")
    assert state.players[1].cash == 750 + 25
    assert "mayonnaise" in state.discovered
    assert any(dict(e.data).get("first") is True for e in events if e.kind == "card")


def test_both_towns_of_the_pair_earn_fifty():
    state = own(_drawing("mayonnaise", EVENT, 0), 1, *BROWN, *ORANGE)
    state, _ = apply(state, "roll")
    assert state.players[1].cash == 750 + 50


def test_an_intelligent_disaster_destroys_the_most_expensive_buildings_first():
    from traveler_quartet.rules.disasters import destroy
    state = build_levels(own(game(), 1, *DARK_BLUE), {37: 1, 39: 1})
    state, destroyed = destroy(state, "dark_blue", count=1, target="expensive")
    assert destroyed == (39,) and state.buildings[39] == 0 and state.buildings[37] == 1
    assert state.houses_left == 32 + 1


def test_a_mindless_disaster_destroys_buildings_at_random_but_reproducibly():
    from traveler_quartet.rules.disasters import destroy
    state = build_levels(own(game(), 1, *DARK_BLUE), {37: 2, 39: 2})
    first = destroy(state, "dark_blue", count=3, target="random")
    assert first == destroy(state, "dark_blue", count=3, target="random")
    assert sum(first[0].buildings[i] for i in DARK_BLUE) == 4 - 3


def test_a_disaster_on_a_town_without_buildings_destroys_nothing():
    from traveler_quartet.rules.disasters import destroy
    assert destroy(game(), "brown", count=2, target="random")[1] == ()


def test_the_die_of_a_disaster_gives_nothing_one_two_or_three_buildings():
    from traveler_quartet.rules.disasters import damage
    assert [damage(face) for face in range(1, 7)] == [1, 0, 2, 0, 3, 0]


def test_an_epidemic_makes_the_capital_owner_pay_thirty_per_building():
    state = build_levels(own(_drawing("epidemic", EVENT, 0), 1, *DARK_BLUE), {37: 1, 39: 1})
    state, _ = apply(state, "roll")
    assert state.players[1].cash == 750 - 30 * 2


def test_the_crisis_costs_half_more_with_the_whole_pair():
    state = own(_drawing("epidemic", EVENT, 0), 1, *DARK_BLUE, *LIGHT_BLUE)
    state = build_levels(state, {37: 1, 39: 1})
    state, _ = apply(state, "roll")
    assert state.players[1].cash == 750 - 30 * 2 * 3 // 2


def test_an_odd_curse_must_be_played_at_once_on_another_player():
    state, _ = apply(_drawing("curse", EVENT, 0, players=3, die_even=False), "roll")
    assert set(legal_actions(state)) == {"curse:1", "curse:2"}


def test_an_even_curse_can_be_kept_and_played_later():
    state, _ = apply(_drawing("curse", EVENT, 0, players=3, die_even=True), "roll")
    assert "curse" in state.players[0].cards


def test_a_curse_makes_its_target_pay_a_crisis_on_his_buildings():
    state = build_levels(own(_drawing("curse", EVENT, 0, players=3, die_even=False), 2, *BROWN), {1: 1, 3: 1})
    state, _ = apply(state, "roll")
    state, _ = apply(state, "curse:2")
    assert state.players[2].cash == 750 - 30 * 2


def test_the_dungeon_draws_an_adventurer_card_before_the_roll():
    seed = _seed(lambda r: r[0][0] != r[0][1])
    state = at(new_game(seed=seed, player_count=2), 0, 10)
    state = replace(state, players=(replace(state.players[0], dungeon_turns=2),) + state.players[1:])
    state = replace(state, decks=tuple((d, ("goblins",) + tuple(c for c in o if c != "goblins")) if d == "adventurer"
                                       else (d, o) for d, o in state.decks))
    state, events = apply(state, "roll")
    assert state.players[0].cash == 750 - 20
    assert any(e.kind == "card" and dict(e.data)["card"] == "goblins" for e in events)
