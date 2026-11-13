"""Every card is in exactly ONE place at every step of a whole game: in its deck, or in one player's hand.

A kept card (the rope, the mirror, a kept curse) leaves its deck; it goes back UNDER its deck when it is played, and a
player who goes out returns his cards the same way. Before this rule, a kept card stayed under its deck too and could
be drawn again while someone held it: two players holding the same mirror."""

from collections import Counter
from dataclasses import replace

import pytest

from factory import at, game
from traveler_quartet.match.runner import play_game_rounds
from traveler_quartet.players.bots import BOTS
from traveler_quartet.rules.card_effects import resolve
from traveler_quartet.rules.cards import deck_of
from traveler_quartet.rules.engine import apply, legal_actions, new_game

SEEDS = range(1, 21)
RETURN_PATHS = {"used_rope", "mirrored", "cursed_from_hand", "bankrupt_with_cards"}


def _places(state):
    held = Counter(card for player in state.players for card in player.cards)
    decked = Counter(card for _, ids in state.decks for card in ids)
    return held + decked


def _paths(before, events):
    found = {event.kind for _, event in events if event.kind in ("used_rope", "mirrored")}
    for _, event in events:
        if event.kind == "cursed" and before.pending == "roll":
            found.add("cursed_from_hand")
        if event.kind == "bankrupt" and before.players[event.player].cards:
            found.add("bankrupt_with_cards")
    return found


def _play_checked(seed):
    initial = new_game(seed=seed, player_count=4)
    expected, seen, last = _places(initial), set(), [initial]

    def on_step(state, events):
        assert _places(state) == expected, f"seed {seed}, round {state.round}: a card is in two places, or lost"
        assert not any(p.cards for p in state.players if p.out), f"seed {seed}: a player who is out still holds cards"
        seen.update(_paths(last[0], events))
        last[0] = state

    play_game_rounds(initial, [BOTS["normal"]] * 4, on_step=on_step)
    return seen


def test_every_card_stays_in_one_place_through_whole_games():
    seen = set()
    for seed in SEEDS:
        seen |= _play_checked(seed)
    assert seen == RETURN_PATHS, f"the games no longer exercise every way back: {sorted(seen)}"


def _on_top(state, card):
    deck = deck_of(state, card)
    return replace(state, decks=tuple((d, (card,) + tuple(c for c in ids if c != card)) if d == deck else (d, ids)
                                      for d, ids in state.decks))


@pytest.mark.parametrize("card", ["rope", "mirror"])
def test_a_kept_card_leaves_its_deck_and_is_not_drawn_again_while_held(card):
    state, _, _ = resolve(_on_top(game(), card), deck_of(game(), card))
    deck = dict(state.decks)[deck_of(state, card)]
    assert card in state.players[0].cards and card not in deck
    drawn = []
    for _ in range(len(deck)):
        state, events, _ = resolve(replace(state, current=1), deck_of(state, card))
        drawn.append(dict(events[0].data)["card"])
    assert card not in drawn


def test_a_played_rope_goes_back_under_its_deck():
    state, _, _ = resolve(_on_top(game(), "rope"), "chance")
    state = at(replace(state, current=0, pending="roll", doubles=0), 0, 10)
    state = replace(state, players=(replace(state.players[0], dungeon_turns=2),) + state.players[1:])
    assert "use_rope" in legal_actions(state)
    state, _ = apply(state, "use_rope")
    assert "rope" not in state.players[0].cards
    assert dict(state.decks)["chance"][-1] == "rope"
