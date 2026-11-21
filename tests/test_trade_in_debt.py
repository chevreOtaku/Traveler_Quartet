"""The offer during a DEBT (D54) -- the RULE since 21/11 (`trade_in_debt` = 1; a table may set it to 0). A debtor
may offer a trade before mortgaging or going bankrupt; the trade comes back to the debt it came from, and the debt is
paid as soon as the cash covers it -- exactly as after a mortgage. The half-to-double rule still holds.

Every state below starts from a REAL debt: a rent the engine charged after a roll, never a state set by hand."""

import json
from dataclasses import replace

import pytest

from factory import at, build_levels, cash, game, own
from traveler_quartet.match.ai_game import play_ai_game
from traveler_quartet.match.replay import replay
from traveler_quartet.match.runner import play_game_rounds
from traveler_quartet.players.command_player import CommandPlayer
from traveler_quartet.players.text import CONTRACT, QUESTIONS, render
from traveler_quartet.players.view import view
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.engine import IllegalAction, actor, apply, legal_actions, negotiations, new_game

DARK_BLUE, PURPLE = (37, 39), (11, 13, 14)
SELL_PURPLE = "offer:2:0:11,13,14::440::"
SELL_ONE = "offer:2:0:11::140::"


def in_debt(option=1, gold=300, talks=0, players=3):
    """Player 0 lands on the creditor's built dark blue (rent 680) with `gold` in hand and the purple town to trade."""
    state = build_levels(own(game(players=players), 1, *DARK_BLUE), {37: 4, 39: 4})
    state = cash(at(own(state, 0, *PURPLE), 0, (37 - sum(roll(state.seed, 0))) % 40), 0, gold)
    state = replace(state, economy=replace(state.economy, trade_in_debt=option, talks_per_turn=talks))
    state, events = apply(state, "roll")
    assert (state.pending, state.debt.amount, state.debt.creditor) == ("debt", 680, 1)
    assert events[-1].kind == "debt_opened"
    return state


def kinds(events):
    return [e.kind for e in events]


def test_the_rule_is_on_by_default_and_a_table_without_it_has_no_offer_in_a_debt():
    assert new_game(seed=1, player_count=3).economy.trade_in_debt == 1
    state = in_debt(option=0)
    assert negotiations(state) == ()
    with pytest.raises(IllegalAction):
        apply(state, SELL_PURPLE)


def test_with_the_option_the_debtor_may_offer_to_every_active_rival_and_nothing_else_changes():
    state = in_debt()
    assert negotiations(state) == ("offer:1", "offer:2")
    assert legal_actions(state) == legal_actions(in_debt(option=0))
    with pytest.raises(IllegalAction):
        apply(state, "offer:2")


@pytest.mark.parametrize("ask, legal", [(35, True), (140, True), (34, False), (141, False)])
def test_the_half_to_double_rule_holds_in_a_debt(ask, legal):
    """A debtor cannot give a district away to a friend, nor be stripped: [11] is worth 70."""
    state = in_debt()
    if legal:
        assert apply(state, f"offer:2:0:11::{ask}::")[0].pending == "trade"
    else:
        with pytest.raises(IllegalAction):
            apply(state, f"offer:2:0:11::{ask}::")


def test_an_accepted_offer_that_covers_the_debt_pays_it_and_ends_the_turn():
    offered, _ = apply(in_debt(), SELL_PURPLE)
    assert (offered.pending, actor(offered), offered.debt.amount) == ("trade", 2, 680)
    done, events = apply(offered, "accept")
    assert kinds(events) == ["trade_done", "debt_paid"]
    assert (done.pending, done.current, done.debt) == ("roll", 1, None)
    assert [p.cash for p in done.players] == [300 + 440 - 680, 750 + 680, 750 - 440]
    assert all(done.owners[i] == 2 for i in PURPLE)


def test_an_accepted_offer_that_does_not_cover_the_debt_comes_back_to_the_same_debt():
    offered, _ = apply(in_debt(), SELL_ONE)
    back, events = apply(offered, "accept")
    assert kinds(events) == ["trade_done"]
    assert (back.pending, back.current, back.debt.amount, back.players[0].cash) == ("debt", 0, 680, 440)
    assert legal_actions(back) == ("mortgage:13", "mortgage:14")
    assert negotiations(back) == ("offer:1", "offer:2")


def test_a_refused_offer_comes_back_to_the_debt_never_to_the_start_of_the_turn():
    offered, _ = apply(in_debt(), SELL_PURPLE)
    back, events = apply(offered, "refuse")
    assert kinds(events) == ["trade_refused"]
    assert (back.pending, back.current, back.debt.amount, back.players[0].cash) == ("debt", 0, 680, 300)
    assert "roll" not in legal_actions(back)


@pytest.mark.parametrize("answer, pending, current", [("accept", "roll", 1), ("refuse", "debt", 0)])
def test_a_counter_offer_keeps_the_debt_it_came_from(answer, pending, current):
    offered, _ = apply(in_debt(), SELL_ONE)
    countered, _ = apply(offered, "counter:440:::0:11,13,14:")
    assert (countered.pending, actor(countered)) == ("trade", 0)
    after, _ = apply(countered, answer)
    assert (after.pending, after.current) == (pending, current)
    assert (after.debt is None) == (answer == "accept")


def test_a_talk_inside_a_trade_from_a_debt_does_not_lose_the_debt():
    """Table talk writes its own `resume`: a talk in the middle of the trade must not overwrite where the trade goes
    back to (the writers of `pending` -- trades, talk -- each in this test)."""
    talked, _ = apply(in_debt(talks=2), "talk:2")
    back, _ = apply(talked, "reply")
    assert back.pending == "debt"
    offered, _ = apply(back, SELL_PURPLE)
    talked, _ = apply(offered, "talk:0")
    assert (talked.pending, actor(talked)) == ("talk", 0)
    replied, _ = apply(talked, "reply")
    assert (replied.pending, actor(replied)) == ("trade", 2)
    refused, _ = apply(replied, "refuse")
    assert (refused.pending, refused.current, refused.debt.amount) == ("debt", 0, 680)


def test_three_negotiations_per_turn_in_a_debt_too():
    state = in_debt()
    for _ in range(3):
        state, _ = apply(state, SELL_PURPLE)
        state, _ = apply(state, "refuse")
    assert negotiations(state) == ()
    assert state.pending == "debt" and "mortgage:11" in legal_actions(state)


@pytest.mark.parametrize("answer", ["accept", "refuse"])
def test_a_trade_at_the_start_of_the_turn_still_comes_back_to_the_start(answer):
    state = own(game(players=3), 0, 11)
    offered, _ = apply(state, "offer:1:0:11::70::")
    after, _ = apply(offered, answer)
    assert (after.pending, after.current) == ("roll", 0)


def test_the_debtor_reads_that_a_trade_is_open_and_the_text_without_the_option_is_unchanged():
    off, on = render(view(in_debt(option=0), 0)), render(view(in_debt(), 0))
    assert f"{QUESTIONS['debt']} (question: `debt`)" in off
    assert "offer a trade" not in off and CONTRACT not in off
    assert "or offer a trade" in on and CONTRACT in on and "Open now: `offer:1`, `offer:2`" in on


def _debtor_sells_then_rival_accepts(prompt):
    choices = [line[3:-1] for line in prompt.splitlines() if line.startswith("- `") and line.endswith("`")]
    if "(question: `debt`)" in prompt and "`offer:2`" in prompt:
        return json.dumps({"action": SELL_PURPLE, "message": "Buy my purple town, I must pay a rent."})
    if "(question: `trade`)" in prompt:
        return json.dumps({"action": "accept", "message": "Deal."})
    return json.dumps({"action": "pass" if "pass" in choices else choices[0], "message": ""})


def test_an_ai_debtor_reads_the_offer_in_its_text_plays_it_and_the_debt_is_paid():
    """From the text to the engine: the command player is asked in the debt, writes the offer, the rival accepts."""
    state = build_levels(own(game(players=3), 1, *DARK_BLUE), {37: 4, 39: 4})
    state = cash(at(own(state, 0, *PURPLE), 0, (37 - sum(roll(state.seed, 0))) % 40), 0, 300)
    state = replace(state, economy=replace(state.economy, trade_in_debt=1, rounds=1))
    seats = [CommandPlayer(_debtor_sells_then_rival_accepts, seat=s) for s in range(3)]
    _, timed = play_game_rounds(state, seats)
    events = [e for _, e in timed]
    flow = [e.kind for e in events if e.kind in ("debt_opened", "offered", "trade_done", "debt_paid", "bankrupt")]
    assert flow[:4] == ["debt_opened", "offered", "trade_done", "debt_paid"]
    assert next(e for e in events if e.kind == "debt_paid").player == 0


def _first_choice(tmp_path):
    script = tmp_path / "first.py"
    script.write_text(
        "import json, re, sys\n"
        "choices = re.findall(r'^- `([^`]+)`$', sys.stdin.read(), re.MULTILINE)\n"
        "print(json.dumps({'action': 'pass' if 'pass' in choices else choices[0], 'message': ''}))\n",
        encoding="utf-8")
    return {"claude": [__import__("sys").executable, str(script)]}


def test_an_ai_table_records_the_option_in_its_report_and_the_replay_uses_it(tmp_path):
    """With the NON-default value: a table that forgets the option would play the default and pass unseen."""
    report = play_ai_game(("claude", "normal"), rounds=1, log_path=tmp_path / "debt.json", trade_in_debt=0,
                          commands=_first_choice(tmp_path))
    assert report["trade_in_debt"] == 0
    _, _, final = replay(report)
    assert final.economy.trade_in_debt == 0


@pytest.mark.parametrize("value", [-1, 2])
def test_an_ai_table_refuses_a_value_other_than_zero_or_one(tmp_path, value):
    with pytest.raises(ValueError):
        play_ai_game(("claude", "normal"), rounds=1, log_path=tmp_path / "bad.json", trade_in_debt=value,
                     commands=_first_choice(tmp_path))


def test_the_human_debt_view_given_to_the_3d_page_is_what_the_engine_sends():
    """The page's test reads `board3d-debt-view.json`: it must be the engine's view of a human in a REAL debt."""
    from pathlib import Path
    from debt_view import TARGET, debt_view
    assert json.loads(Path(TARGET).read_text(encoding="utf-8")) == debt_view()
    seen = debt_view()["view"]
    assert (seen["pending"], seen["negotiations"], seen["debt_context"]) == (
        "debt", ["offer:1", "offer:2"], {"debtor": 0, "to": 1, "amount": 680})
