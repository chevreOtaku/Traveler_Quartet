"""What a SPECTATOR sees (the OBS scene of a stream, step 7) and the length of a game set at creation. A spectator holds
no seat and no token: the same public facts as a player's view -- the board, every player's public line, the order of
the round, the rules -- but no one's kept cards, no sealed bid, no legal action, no way to play. Filtered by the server,
not hidden on screen."""

import json
from dataclasses import replace

from factory import game
from traveler_quartet.match.server import Registry, handle
from traveler_quartet.players.view import spectator

PERMITTED_TOP = {"round", "rounds", "current", "pending", "last_dice", "jackpot", "houses_left", "stalls_left", "players",
                 "board", "order", "doubles", "rules", "cards", "actor"}
PERMITTED_WHEN_OPEN = {"auction", "trade", "stall_request", "sealed", "debt_context", "ranking"}


def _with_cards(state, player, cards):
    players = list(state.players)
    players[player] = replace(players[player], cards=cards)
    return replace(state, players=tuple(players))


def _create(reg, body):
    return handle(reg, "POST", "/games", {}, json.dumps(body).encode())


def test_the_spectator_view_holds_only_public_keys_and_every_player():
    seen = spectator(game(players=3))
    assert set(seen) - PERMITTED_WHEN_OPEN == PERMITTED_TOP and [p["seat"] for p in seen["players"]] == [0, 1, 2]


def test_a_spectator_never_sees_a_kept_card_nor_a_way_to_play():
    seen = spectator(_with_cards(game(players=3), 1, ("mirror",)))
    assert "mirror" not in json.dumps(seen["players"]) and seen["players"][1]["cards_held"] == 1
    assert "legal_actions" not in seen and "negotiations" not in seen and "me" not in seen


def test_a_spectator_never_sees_a_sealed_bid():
    from traveler_quartet.rules.auctions import Sealed
    state = replace(game(players=3), pending="sealed", sealed=Sealed(queue=(6,), bidders=(0, 1, 2), turn=2, bids=(40, 55)))
    seen = spectator(state)
    assert seen["sealed"] == {"square": 6, "bids_written": 2} and "55" not in json.dumps(seen["sealed"])


def test_the_server_shows_a_game_to_a_spectator_without_a_token():
    reg = Registry()
    _, created = _create(reg, {"seats": ["remote", "normal"], "seed": 1})
    status, body = handle(reg, "GET", f"/games/{created['game']}/public", {}, b"")
    assert status == 200 and "players" in body["view"] and "text" not in body and body["over"] is False


def test_the_spectator_log_hides_every_kept_card():
    from traveler_quartet.rules.state import Event
    reg = Registry()
    _, created = _create(reg, {"seats": ["remote", "normal"], "seed": 1})
    session = reg.games[created["game"]]
    session.log.append((1, Event("card", 0, (("card", "mirror"),))))
    status, body = handle(reg, "GET", f"/games/{created['game']}/public/events?since=0", {}, b"")
    assert status == 200 and "mirror" not in json.dumps(body["events"]) and body["events"][-1]["data"]["card"] == "a kept card"


def test_a_sealed_bid_said_with_a_message_never_leaks_its_amount():
    """Found by Codex in review (P1): a message recorded the exact action `bid:55` -- the server published it."""
    from traveler_quartet.rules.auctions import Sealed
    reg = Registry()
    _, created = _create(reg, {"seats": ["remote", "remote", "remote"], "seed": 1})
    game, tokens = created["game"], {seat: token for token, seat in created["tokens"].items()}
    session = reg.games[game]
    session.state = replace(session.state, pending="sealed", current=0,
                            sealed=Sealed(queue=(6,), bidders=(0, 1, 2), turn=0, bids=()))
    acted = handle(reg, "POST", f"/games/{game}/act", {"Authorization": f"Bearer {tokens[0]}"},
                   json.dumps({"action": "bid:55", "message": "hello"}).encode())
    assert acted[0] == 200 and reg.games[game].state.pending == "sealed"
    public = handle(reg, "GET", f"/games/{game}/public/events?since=0", {}, b"")[1]["events"]
    rival = handle(reg, "GET", f"/games/{game}/events?since=0", {"Authorization": f"Bearer {tokens[1]}"}, b"")[1]["events"]
    mine = handle(reg, "GET", f"/games/{game}/events?since=0", {"Authorization": f"Bearer {tokens[0]}"}, b"")[1]["events"]
    said = lambda events: next(e for e in events if e["kind"] == "said")
    assert "55" not in json.dumps(public) and "55" not in json.dumps(rival)
    assert said(public)["data"] == {"action": "bid", "text": "hello"} and said(rival)["data"]["text"] == "hello"
    assert said(mine)["data"]["action"] == "bid:55"


def test_an_open_auction_raise_stays_public():
    from traveler_quartet.players.recent import public_event
    from traveler_quartet.rules.state import Event
    raised = Event("said", 0, (("action", "raise:10"), ("text", "more")))
    assert public_event(game().catalog, raised, None)["data"]["action"] == "raise:10"


def test_a_game_can_be_created_shorter():
    reg = Registry()
    status, created = _create(reg, {"seats": ["remote", "normal"], "seed": 1, "rounds": 5})
    token = next(iter(created["tokens"]))
    view = handle(reg, "GET", f"/games/{created['game']}/view", {"Authorization": f"Bearer {token}"}, b"")[1]["view"]
    assert status == 201 and view["rounds"] == 5


def test_a_wrong_length_is_refused():
    for rounds in (0, -3, "ten"):
        assert _create(Registry(), {"seats": ["remote", "normal"], "seed": 1, "rounds": rounds})[0] == 400
