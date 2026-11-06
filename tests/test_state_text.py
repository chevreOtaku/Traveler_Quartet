"""The state as TEXT (step 7): what a human reads in the console and what an AI player reads at each decision. Built
ONLY from `view` -- so it cannot show a secret that the view hides."""

from dataclasses import replace

from factory import game, own
from traveler_quartet.players.text import render
from traveler_quartet.players.view import view
from traveler_quartet.rules.engine import apply, legal_actions


def _with_cards(state, player, cards):
    players = list(state.players)
    players[player] = replace(players[player], cards=cards)
    return replace(state, players=tuple(players))


def test_the_text_says_the_round_my_cash_and_where_i_stand():
    text = render(view(game(), 0))
    assert "Round 1 / 30" in text and "750 gold" in text and game().board.squares[0].name in text


def test_every_legal_action_is_listed_when_it_is_my_turn():
    state = game()
    text = render(view(state, 0))
    assert all(f"`{a}`" in text for a in legal_actions(state))


def test_when_it_is_not_my_turn_no_action_is_offered():
    assert "Your choices" not in render(view(game(), 1))


def test_the_others_kept_cards_never_appear_only_their_number():
    state = _with_cards(game(players=3), 1, ("mirror",))
    text = render(view(state, 0))
    assert "mirror" not in text and "1 kept card" in text


def test_what_i_own_is_listed_with_its_town():
    text = render(view(own(game(), 0, 1, 3), 0))
    assert "brown" in text and game().board.squares[1].name in text


def test_the_contract_of_an_offer_is_explained_when_i_may_offer():
    state = own(own(game(players=2), 0, 1), 1, 3)
    text = render(view(state, 0))
    assert "offer:" in text and "give_gold" in text


def test_a_question_to_answer_is_said_in_words():
    from traveler_quartet.players.text import QUESTIONS
    from traveler_quartet.rules.engine import actor
    state, _ = apply(game(), "roll")
    text = render(view(state, actor(state)))
    assert QUESTIONS[state.pending] in text and f"`{state.pending}`" in text
