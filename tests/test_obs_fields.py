"""The public fields an OBS scene needs (asked by the front, 07/11), all PUBLIC on the table: who must answer now
(`actor`, distinct from `current`), the context of a debt, a shared stall's partner, the final ranking, and each logged
event as a sentence -- from the spectator's side, no "you"."""

import json
from dataclasses import replace

from factory import game
from traveler_quartet.match.server import Registry, handle
from traveler_quartet.players.view import spectator, view
from traveler_quartet.rules.endgame import ranking
from traveler_quartet.rules.state import Debt


def test_the_actor_is_who_must_answer_not_whose_turn_it_is():
    from traveler_quartet.rules.trades import Terms, Trade
    state = replace(game(players=3), pending="trade", current=0,
                    trade=Trade(proposer=0, responder=2, terms=Terms(give_gold=10), counters=0))
    assert spectator(state)["actor"] == 2 and view(state, 1)["actor"] == 2 and spectator(state)["current"] == 0


def test_after_the_game_there_is_no_actor_and_the_ranking_is_given():
    over = replace(game(players=3), pending="over")
    seen = spectator(over)
    assert seen["actor"] is None
    assert seen["ranking"] == [{"seat": seat, "net_worth": worth} for seat, worth in ranking(over)]
    assert "ranking" not in spectator(game(players=3))


def test_a_debt_says_who_owes_whom_and_how_much():
    base = replace(game(players=3), pending="debt", current=1)
    assert spectator(replace(base, debt=Debt(80, creditor=2)))["debt_context"] == {"debtor": 1, "to": 2, "amount": 80}
    assert spectator(replace(base, debt=Debt(50, creditor=None)))["debt_context"]["to"] == "bank"
    assert spectator(replace(base, debt=Debt(30, creditor=None, to_jackpot=True)))["debt_context"]["to"] == "jackpot"
    assert "debt_context" not in spectator(game(players=3))


def test_a_shared_stall_shows_its_partner():
    state = game(players=3)
    partners = tuple(2 if i == 6 else None for i in range(len(state.owners)))
    seen = spectator(replace(state, partners=partners))
    assert seen["board"][6]["partner"] == 2 and seen["board"][8]["partner"] is None


def test_each_logged_event_carries_a_sentence_from_the_right_side():
    reg = Registry()
    _, created = handle(reg, "POST", "/games", {}, json.dumps({"seats": ["remote", "normal"], "seed": 1}).encode())
    game_id, token = created["game"], next(iter(created["tokens"]))
    handle(reg, "POST", f"/games/{game_id}/act", {"Authorization": f"Bearer {token}"},
           json.dumps({"action": "roll", "message": "hi"}).encode())
    public = handle(reg, "GET", f"/games/{game_id}/public/events?since=0", {}, b"")[1]["events"]
    mine = handle(reg, "GET", f"/games/{game_id}/events?since=0", {"Authorization": f"Bearer {token}"}, b"")[1]["events"]
    assert public and all(e["sentence"] for e in public) and not any(e["sentence"].startswith("you") for e in public)
    assert any(e["sentence"] == 'you said: "hi"' for e in mine)
    assert any(e["sentence"] == 'player 0 said: "hi"' for e in public)
