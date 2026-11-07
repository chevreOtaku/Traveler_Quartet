"""The view also shows the PUBLIC facts (D47): a human has the rule book, an AI player has only the view. Rents as
they are now, the order of the round, a double, every player's net worth, the amounts of the rules and the card
CATALOGUE -- never the order of the decks, the seed, the others' kept cards or sealed bids. A guard lists the keys the
view may hold: a new key fails here until it is added by hand, with its public reason."""

from dataclasses import fields, replace

from factory import build_levels, game, own
from traveler_quartet.players.view import view
from traveler_quartet.rules.endgame import net_worth

LIGHT_BLUE = (6, 8, 9)
PERMITTED_TOP = {"round", "rounds", "current", "pending", "last_dice", "jackpot", "houses_left", "stalls_left", "me",
                 "others", "board", "your_turn", "legal_actions", "negotiations", "order", "doubles", "rules", "cards",
                 "actor"}
PERMITTED_WHEN_OPEN = {"auction", "trade", "stall_request", "debt", "sealed", "debt_context", "ranking"}
PERMITTED_SQUARE = {"index", "name", "kind", "town", "price", "owner", "buildings", "mortgaged", "rent",
                    "rent_per_dice_point", "partner"}
PERMITTED_PLAYER = {"seat", "cash", "position", "out", "in_dungeon", "cards_held", "net_worth"}


def _square_of_kind(state, kind):
    return next(i for i, s in enumerate(state.board.squares) if s.kind == kind)


def test_the_view_holds_only_the_permitted_keys():
    seen = view(game(players=3), 0)
    assert set(seen) - PERMITTED_WHEN_OPEN == PERMITTED_TOP
    assert all(set(sq) == PERMITTED_SQUARE for sq in seen["board"])
    assert set(seen["me"]) == PERMITTED_PLAYER | {"cards"}
    assert all(set(o) == PERMITTED_PLAYER for o in seen["others"])


def test_a_district_shows_the_rent_a_visitor_would_pay_now():
    state = own(game(), 1, 6)
    price = state.board.squares[6].price
    assert view(state, 0)["board"][6]["rent"] == price * 10 // 100
    whole = own(state, 1, *LIGHT_BLUE)
    assert view(whole, 0)["board"][6]["rent"] == 2 * (price * 10 // 100)
    built = build_levels(whole, {6: 2})
    assert view(built, 0)["board"][6]["rent"] == 10 * (price * 10 // 100)


def test_a_free_or_mortgaged_property_shows_no_rent():
    state = own(game(), 1, 6)
    mortgaged = replace(state, mortgaged=tuple(i == 6 for i in range(len(state.owners))))
    assert view(game(), 0)["board"][6]["rent"] == 0 and view(mortgaged, 0)["board"][6]["rent"] == 0


def test_a_portal_shows_its_rent_and_a_utility_its_dice_multiplier():
    state = game()
    portal, utility = _square_of_kind(state, "portal"), _square_of_kind(state, "utility")
    seen = view(own(state, 1, portal, utility), 0)
    assert seen["board"][portal]["rent"] == state.economy.portal_rent
    assert seen["board"][utility]["rent"] is None
    assert seen["board"][utility]["rent_per_dice_point"] == state.economy.utility_multiplier
    assert seen["board"][portal]["rent_per_dice_point"] is None


def test_the_order_of_the_round_is_shown_and_skips_the_eliminated():
    state = replace(game(players=4), round=2)
    assert view(state, 0)["order"] == [1, 2, 3, 0]
    players = list(state.players)
    players[2] = replace(players[2], out=True)
    assert view(replace(state, players=tuple(players)), 0)["order"] == [1, 3, 0]


def test_a_double_is_shown():
    assert view(game(), 0)["doubles"] == 0 and view(replace(game(), doubles=1), 1)["doubles"] == 1


def test_every_net_worth_is_shown_as_the_final_score_counts_it():
    state = build_levels(own(game(players=3), 1, *LIGHT_BLUE), {6: 1})
    seen = view(state, 0)
    assert seen["me"]["net_worth"] == net_worth(state, 0)
    assert [o["net_worth"] for o in seen["others"]] == [net_worth(state, 1), net_worth(state, 2)]


def test_the_rules_amounts_are_the_rule_book():
    state = game()
    rules = view(state, 0)["rules"]
    assert set(rules) == {f.name for f in fields(state.economy)} and rules["rent_percent"] == state.economy.rent_percent


def test_the_card_catalogue_is_public_but_never_the_order_of_the_decks():
    one, other = view(game(seed=1), 0), view(game(seed=2), 0)
    assert {c["id"] for c in one["cards"]} == set(game().catalog)
    assert one["cards"] == other["cards"] and "decks" not in one
