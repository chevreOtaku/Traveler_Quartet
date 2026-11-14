"""How an AI seat SEES and WRITES a trade offer -- three styles, one difference each:
- `fields` (the default): the contract's six positional fields, explained under the list of choices;
- `named`: the same place, the offer written with NAMED fields (a JSON object), translated into the contract;
- `listed`: the same syntax, each open offer IN the list of choices.
Only the offer part of the text changes; the engine, its events and the replay never see the style."""

import json
import sys
from dataclasses import replace

import pytest

from factory import at, game, own
from traveler_quartet.match.ai_game import play_ai_game
from traveler_quartet.match.replay import replay
from traveler_quartet.players.command_player import CommandPlayer, contract_action
from traveler_quartet.players.text import CONTRACT, OFFER_STYLES, render
from traveler_quartet.players.view import view
from traveler_quartet.rules.engine import legal_actions
from traveler_quartet.rules.trades import Terms, Trade

TEMPLATE = "<give_gold>:<give_squares>:<give_cards>:<ask_gold>:<ask_squares>:<ask_cards>"


class Scripted:
    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.answers.pop(0)


def _roll():
    """Player 0 starts a turn; offers to player 1 are open (player 0 owns [1], player 1 owns [3])."""
    return own(own(game(players=2), 0, 1), 1, 3)


def _trade_question():
    state = own(own(game(), 0, 3), 1, 1)
    trade = Trade(proposer=1, responder=0, terms=Terms(give_gold=45, ask_squares=(3,)), counters=0)
    return replace(state, pending="trade", current=0, trade=trade)


def _lines(state, style):
    return render(view(state, 0), style).splitlines()


def test_fields_is_the_default_and_the_contract_stays_under_the_choices():
    seen = view(_roll(), 0)
    text = render(seen)
    assert text == render(seen, "fields")
    assert CONTRACT in text and "Open now: `offer:1`" in text
    assert not any(line.startswith("- `offer:") for line in text.splitlines())


def test_listed_puts_each_open_offer_in_the_list_of_choices():
    lines = _lines(_roll(), "listed")
    assert any(line.startswith(f"- `offer:1:{TEMPLATE}`") for line in lines)
    assert CONTRACT in lines and not any(line.startswith("Open now") for line in lines)


def test_listed_puts_the_counter_offer_in_the_list_at_a_trade_question():
    lines = _lines(_trade_question(), "listed")
    assert any(line.startswith(f"- `counter:{TEMPLATE}`") for line in lines)
    assert "- `accept`" in lines and "- `refuse`" in lines


def test_named_writes_the_offer_with_named_fields_at_the_same_place():
    text = render(view(_roll(), 0), "named")
    assert '"to": <player>' in text and '"give"' in text and '"ask"' in text and "Open now: `offer` to player 1" in text
    assert "offer:<player>" not in text and not any(line.startswith("- `offer") for line in text.splitlines())
    at_trade = render(view(_trade_question(), 0), "named")
    assert '"action": "counter"' in at_trade and "Open now: `counter`" in at_trade


@pytest.mark.parametrize("state", [_roll(), _trade_question()])
def test_only_the_offer_part_of_the_text_changes(state):
    base = _lines(state, "fields")
    last_choice = max(i for i, line in enumerate(base) if line.startswith("- `"))
    for style in OFFER_STYLES:
        assert _lines(state, style)[: last_choice + 1] == base[: last_choice + 1]


def test_without_an_open_negotiation_every_style_reads_the_same():
    seen = view(replace(at(own(game(), 0, 16), 0, 18), pending="buy"), 0)
    assert render(seen, "fields") == render(seen, "named") == render(seen, "listed")


def test_an_unknown_style_is_refused():
    with pytest.raises(ValueError, match="style"):
        render(view(_roll(), 0), "free")
    with pytest.raises(ValueError, match="style"):
        CommandPlayer(Scripted(), seat=0, offer_style="free")


@pytest.mark.parametrize("reply, contract", [
    ({"action": "offer", "to": 1, "give": {"gold": 40}, "ask": {"squares": [3]}}, "offer:1:40:::0:3:"),
    ({"action": "offer", "to": 2, "give": {"squares": [6, 8], "cards": ["rope"]}, "ask": {"gold": 120}},
     "offer:2:0:6,8:rope:120::"),
    ({"action": " counter ", "give": {"squares": [3]}, "ask": {"gold": 10}}, "counter:0:3::10::"),
])
def test_a_named_offer_becomes_the_engines_contract(reply, contract):
    assert contract_action(reply) == contract


@pytest.mark.parametrize("reply", [
    {"action": "roll"},
    {"action": "offer", "give": {"gold": 40}, "ask": {"gold": 30}},
    {"action": "offer", "to": "one", "give": {"gold": 40}},
    {"action": "offer", "to": 1, "give": {"gold": "40"}, "ask": {"gold": 30}},
    {"action": "offer", "to": 1, "give": {"gold": True}, "ask": {"gold": 30}},
    {"action": "offer", "to": 1, "give": {"squares": "16"}, "ask": {"gold": 30}},
    {"action": "offer", "to": 1, "give": {"cards": ["a:b"]}, "ask": {"gold": 30}},
    {"action": "offer", "to": 1, "give": {"cards": "rope"}, "ask": {"gold": 30}},
    {"action": "offer", "to": 1, "give": [40], "ask": {"gold": 30}},
])
def test_what_is_not_a_named_offer_gives_no_contract(reply):
    assert contract_action(reply) is None


def test_a_named_offer_is_played_as_the_engines_contract():
    state = _roll()
    ai = Scripted('{"action": "offer", "to": 1, "give": {"gold": 40}, "ask": {"squares": [3]}, "message": "deal?"}')
    played = CommandPlayer(ai, seat=0, offer_style="named")(state, legal_actions(state))
    assert played == ("offer:1:40:::0:3:", "deal?") and '"to": <player>' in ai.prompts[0]


def test_a_named_offer_the_engine_refuses_is_asked_again():
    state = _roll()
    ai = Scripted('{"action": "offer", "to": 1, "give": {"gold": 40}, "ask": {"squares": [5]}}',
                  '{"action": "roll", "message": ""}')
    assert CommandPlayer(ai, seat=0, offer_style="named")(state, legal_actions(state)) == ("roll", None)
    assert "offer:1:40:::0:5:" in ai.prompts[1] and "not legal" in ai.prompts[1]


def test_the_fields_style_does_not_read_named_offers():
    state = _roll()
    ai = Scripted('{"action": "offer", "to": 1, "give": {"gold": 40}, "ask": {"squares": [3]}}',
                  '{"action": "roll", "message": ""}')
    assert CommandPlayer(ai, seat=0)(state, legal_actions(state)) == ("roll", None)


@pytest.fixture
def style_echo(tmp_path):
    """A fake AI seat that says which offer text it was shown."""
    script = tmp_path / "style_player.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "seen = 'named' if '\"to\": <player>' in prompt else 'listed' if '-- a trade with player' in prompt else 'fields'\n"
        "action = 'pass' if 'pass' in choices else choices[0]\n"
        "print(json.dumps({'action': action, 'message': seen}))\n", encoding="utf-8")
    return [sys.executable, str(script)]


@pytest.mark.parametrize("style", OFFER_STYLES)
def test_every_ai_seat_reads_its_tables_offer_style_and_the_report_keeps_it(style, tmp_path, style_echo):
    report = play_ai_game(("claude", "claude"), rounds=1, log_path=tmp_path / "s.json", commands={"claude": style_echo},
                          offer_style=style)
    firsts = [event["text"] for event in report["said"] if event["action"] == "roll"]
    assert report["offer_style"] == style and firsts and set(firsts) == {style}


@pytest.mark.parametrize("seats", [("claude", "normal"), ("normal", "normal")])
def test_an_unknown_offer_style_is_refused_before_a_command_runs(seats, tmp_path, style_echo):
    with pytest.raises(ValueError, match="style"):
        play_ai_game(seats, log_path=tmp_path / "never.json", commands={"claude": style_echo}, offer_style="free")
    assert not (tmp_path / "never.json").exists()


def test_a_game_with_named_offers_is_written_and_replayed_with_the_engines_contract(tmp_path):
    script = tmp_path / "trader.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "if '(question: `roll`)' in prompt and 'Open now: `offer` to player 1' in prompt:\n"
        "    print(json.dumps({'action': 'offer', 'to': 1, 'give': {'gold': 40}, 'ask': {'gold': 30},"
        " 'message': 'gold for gold'}))\n"
        "else:\n"
        "    print(json.dumps({'action': 'pass' if 'pass' in choices else choices[0], 'message': ''}))\n",
        encoding="utf-8")
    target = tmp_path / "named.json"
    report = play_ai_game(("claude", "normal"), rounds=2, log_path=target, offer_style="named",
                          commands={"claude": [sys.executable, str(script)]})
    offered = [event for event in report["events"] if event["kind"] == "offered"]
    assert offered and all(event["player"] == 0 and event["data"]["terms"]["give_gold"] == 40 for event in offered)
    assert any(event["action"] == "offer:1:40:::30::" for event in report["said"])
    assert report["fallbacks"] == 0 and json.loads(target.read_text(encoding="utf-8")) == report
    decisions, _, _ = replay(report)
    assert any(decision.action == "offer:1:40:::30::" for decision in decisions)
