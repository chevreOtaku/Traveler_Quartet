"""The engine's public MOVEMENT and TRADE payloads (contract v2, agreed with the front 07/11). One `moved` event per real
movement: who, from, to, why (dice / card / portal / dungeon) and how (a WALK with signed steps, or a TELEPORT) -- the
front never infers a direction. Trade events carry the proposer, the responder and the terms from the PROPOSER's side;
`trade_done` keeps the exact accepted contract. Events are added; the rules do not change."""

from dataclasses import replace

from factory import at, game, own
from traveler_quartet.rules import card_effects, dungeon, portals, trades
from traveler_quartet.rules.engine import apply
from traveler_quartet.rules.trades import Terms

SIZE = len(game().board.squares)


def _kinds(events):
    return [e.kind for e in events]


def _data(events, kind, player=0):
    event = next(e for e in events if e.kind == kind)
    assert event.player == player
    return dict(event.data)


def _card(state, cid):
    return {**state.catalog[cid], "id": cid}


def test_a_dice_move_is_a_forward_walk_that_wraps_past_start():
    state = at(game(), 0, 38)
    state, events = apply(state, "roll")
    dice = sum(_data(events, "rolled")["dice"])
    moved = _data(events, "moved")
    assert moved == {"from": 38, "to": (38 + dice) % SIZE, "kind": "dice", "travel": "walk", "steps": dice}
    kinds = _kinds(events)
    assert kinds.index("rolled") < kinds.index("moved") < kinds.index("passed_start")


def test_going_back_three_is_a_backward_walk_even_across_start():
    state, events, _ = card_effects.move_back(at(game(), 0, 1), _card(game(), "cart"))
    assert _kinds(events) == ["card", "moved"]
    assert _data(events, "moved") == {"from": 1, "to": SIZE - 2, "kind": "card", "travel": "walk",
                                      "steps": -3}


def test_the_card_to_start_walks_forward_and_keeps_its_one_payment():
    start = at(game(), 0, 7)
    state, events, _ = card_effects.move_to_start(start, _card(start, "to_start"))
    assert _kinds(events) == ["card", "moved", "passed_start"]
    assert _data(events, "moved") == {"from": 7, "to": 0, "kind": "card", "travel": "walk",
                                      "steps": SIZE - 7}
    assert state.players[0].cash - start.players[0].cash == _data(events, "passed_start")["amount"]


def test_a_move_already_at_its_destination_fabricates_no_walk():
    _, events, _ = card_effects.move_to_start(at(game(), 0, 0), _card(game(), "to_start"))
    assert "moved" not in _kinds(events) and "passed_start" in _kinds(events)


def test_the_card_to_the_dungeon_is_a_teleport():
    state = at(game(), 0, 7)
    _, events, _ = card_effects.go_to_dungeon(state, _card(state, "to_dungeon"))
    assert _kinds(events) == ["card", "sent_to_dungeon", "moved"]
    assert _data(events, "moved") == {"from": 7, "to": dungeon.dungeon_square(state), "kind": "card",
                                      "travel": "teleport", "steps": None}


def test_three_doubles_send_to_the_dungeon_as_a_teleport_of_kind_dungeon():
    _, events = dungeon.send_to_dungeon(at(game(), 0, 22))
    assert _data(events, "moved")["kind"] == "dungeon" and _data(events, "moved")["travel"] == "teleport"


def test_a_portal_jump_is_one_teleport_after_the_legacy_event_and_before_the_payment():
    state = game()
    last = max(i for i, s in enumerate(state.board.squares) if s.kind == "portal")
    state = at(own(state, 0, last), 0, last)
    state = replace(state, players=tuple(
        replace(p, jump_ready=True) if seat == 0 else p for seat, p in enumerate(state.players)))
    _, events = portals.jump(state)
    assert _kinds(events) == ["jumped", "moved", "passed_start"]
    moved = _data(events, "moved")
    assert moved["kind"] == "portal" and moved["travel"] == "teleport" and moved["steps"] is None
    assert (moved["from"], moved["to"]) == (_data(events, "jumped")["from"], _data(events, "jumped")["to"])


def test_a_move_reads_as_a_sentence_with_its_direction():
    from traveler_quartet.players.recent import sentence
    names = [s.name for s in game().board.squares]
    back = {"kind": "moved", "player": 2, "data": {"from": 1, "to": 38, "kind": "card", "travel": "walk", "steps": -3}}
    jump = {"kind": "moved", "player": 2, "data": {"from": 5, "to": 15, "kind": "portal", "travel": "teleport",
                                                   "steps": None}}
    assert sentence(back, names, None) == f"player 2 went back 3 squares to [38] {names[38]}"
    assert sentence(jump, names, 2) == f"you teleported to [15] {names[15]} (portal)"


def test_trade_events_carry_proposer_responder_and_terms_from_the_proposers_side():
    state = own(own(game(players=4), 1, 6), 3, 18)
    state = replace(state, current=1)
    state, offered = trades.offer(state, 3, Terms(give_gold=40, ask_squares=(18,)))
    assert _data(offered, "offered", player=1) == {"to": 3, "proposer": 1, "responder": 3,
                                          "terms": {"give_gold": 40, "give_squares": [], "give_cards": [], "ask_gold": 0,
                                                    "ask_squares": [18], "ask_cards": []}}
    state, countered = trades.counter(state, Terms(give_squares=(18,), ask_gold=70))
    counter = _data(countered, "countered", player=3)
    assert (counter["proposer"], counter["responder"]) == (3, 1) and counter["terms"]["ask_gold"] == 70
    state, done = trades.accept(state)
    accepted = _data(done, "trade_done", player=1)
    assert (accepted["proposer"], accepted["responder"]) == (3, 1)
    assert accepted["terms"]["give_squares"] == [18] and accepted["terms"]["ask_gold"] == 70
    assert state.owners[18] == 1 and state.trade is None
