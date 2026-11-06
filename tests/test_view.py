"""What a player may SEE (step 7, decision D34): his own kept cards, never the others' (the karma mirror is secret) ;
never the others' sealed bids ; never the FUTURE -- the order of the decks, nor the seed the dice come from. The same
view for a human, a computer or an AI: one source, read by the text, the page and the AI player."""

from dataclasses import replace

from factory import game, own
from traveler_quartet.players.view import view
from traveler_quartet.rules.engine import legal_actions


def _with_cards(state, player, cards):
    players = list(state.players)
    players[player] = replace(players[player], cards=cards)
    return replace(state, players=tuple(players))


def test_a_player_sees_his_own_kept_cards_but_only_how_many_the_others_hold():
    state = _with_cards(_with_cards(game(players=3), 0, ("mirror",)), 1, ("curse", "rope"))
    seen = view(state, 0)
    assert seen["me"]["cards"] == ["mirror"]
    assert seen["others"][0]["cards_held"] == 2 and "cards" not in seen["others"][0]
    assert "mirror" not in str(view(state, 1)["others"])


def test_nobody_sees_the_future_neither_the_decks_nor_the_seed():
    seen = view(game(), 0)
    assert "decks" not in seen and "seed" not in seen and "rolls" not in seen


def test_the_board_is_public():
    seen = view(own(game(), 1, 6), 0)
    assert seen["board"][6]["owner"] == 1 and seen["board"][6]["name"] == game().board.squares[6].name


def test_the_legal_actions_are_given_only_to_the_player_who_must_answer():
    state = game()
    assert view(state, 0)["your_turn"] is True and view(state, 0)["legal_actions"] == list(legal_actions(state))
    assert view(state, 1)["your_turn"] is False and view(state, 1)["legal_actions"] == []


def test_the_others_sealed_bids_are_hidden():
    from traveler_quartet.rules.auctions import Sealed
    state = replace(game(players=3), pending="sealed", sealed=Sealed(queue=(6,), bidders=(0, 1, 2), turn=2, bids=(40, 55)))
    seen = view(state, 2)
    assert "55" not in str(seen.get("sealed")) and seen["sealed"]["bids_written"] == 2


def test_a_mortgage_is_public_it_tells_who_pays_no_rent():
    state = own(game(), 1, 6)
    state = replace(state, mortgaged=tuple(i == 6 for i in range(len(state.owners))))
    assert view(state, 0)["board"][6]["mortgaged"] is True
