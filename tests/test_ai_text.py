"""The text an AI player reads uses the PUBLIC facts of the view (D47), and stays short: who plays in what order, a
double, every net worth, the rent of what is owned, each town and who holds its districts, what a free district costs,
the rules in one line, my own cards' effects, an offer in words. Still built ONLY from the view."""

from dataclasses import replace

from factory import at, build_levels, game, own
from traveler_quartet.players.text import render
from traveler_quartet.players.view import view

ORANGE = (16, 18, 19)


def _text(state, me=0):
    return render(view(state, me))


def test_the_order_of_the_round_is_said():
    assert "Order this round: player 1, player 2, player 3, you" in _text(replace(game(players=4), round=2, current=1))


def test_a_double_is_said_to_the_player_who_rolls_again():
    state = replace(game(), doubles=1)
    said = "You rolled a double: you play again."
    assert said in _text(state, 0) and said not in _text(state, 1) and said not in _text(game(), 0)


def test_every_net_worth_is_said():
    seen = view(own(game(), 1, 6), 0)
    text = render(seen)
    assert f"net worth {seen['me']['net_worth']}" in text and f"net worth {seen['others'][0]['net_worth']}" in text


def test_an_owned_district_says_its_rent():
    state = own(game(), 1, 6)
    assert f"rent {view(state, 0)['board'][6]['rent']}" in _text(state)


def test_each_town_says_who_holds_its_districts():
    text = _text(own(own(game(players=3), 0, 16), 2, 19))
    line = next(l for l in text.splitlines() if l.startswith("- orange"))
    assert "[16] you" in line and "[18] free" in line and "[19] player 2" in line


def test_a_free_district_to_buy_says_its_price_and_its_town():
    state = replace(at(own(game(), 0, 16), 0, 18), pending="buy")
    price = state.board.squares[18].price
    assert f"price {price}" in _text(state) and "you own 1 of 3 in orange" in _text(state)


def test_the_rules_are_said_in_one_line():
    line = next(l for l in _text(game()).splitlines() if l.startswith("Rules:"))
    assert f"{game().economy.rent_percent} % of the price" in line and "whole town" in line


def test_my_kept_cards_say_what_they_do():
    players = list(game().players)
    players[0] = replace(players[0], cards=("rope",))
    text = _text(replace(game(), players=tuple(players)))
    assert "rope" in text and "out of the dungeon" in text


def test_an_offer_is_said_in_words_with_district_names():
    from traveler_quartet.rules.trades import Terms, Trade
    state = own(own(game(), 0, 3), 1, 1)
    terms = Terms(give_gold=45, give_squares=(), give_cards=(), ask_gold=0, ask_squares=(3,), ask_cards=())
    state = replace(state, pending="trade", current=0, trade=Trade(proposer=1, responder=0, terms=terms, counters=0))
    text = _text(state)
    assert "Player 1 offers you 45 gold" in text and state.board.squares[3].name in text and "{'" not in text


def test_an_auction_without_a_bid_says_nobody_leads():
    from traveler_quartet.rules.auctions import Auction
    state = replace(game(), pending="auction", auction=Auction(square=6, price=0, leader=None, bidders=(0, 1)))
    assert "None" not in _text(state) and "nobody" in _text(state)


def test_a_name_ending_with_a_period_gets_no_second_one():
    state = at(game(), 0, 12)
    assert ".." not in _text(state)
