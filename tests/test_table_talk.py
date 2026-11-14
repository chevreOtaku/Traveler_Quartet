"""Table talk -- an option, OFF by default (`talks_per_turn` = 0): at the start of its turn a player may speak to one
rival, who must answer before the turn goes on. The words travel as table messages; the engine gives the floor and
takes it back."""

import json
import sys
from dataclasses import replace

import pytest

from factory import game
from traveler_quartet.match.ai_game import play_ai_game
from traveler_quartet.match.replay import replay
from traveler_quartet.match.runner import play_game_rounds
from traveler_quartet.match.tournament import COMPUTERS
from traveler_quartet.players.command_player import CommandPlayer
from traveler_quartet.players.text import render
from traveler_quartet.players.view import view
from traveler_quartet.rules.engine import IllegalAction, actor, apply, legal_actions, negotiations, new_game
from traveler_quartet.rules.turns import end_turn


def talking(players=3, per_turn=2):
    state = game(players=players)
    return replace(state, economy=replace(state.economy, talks_per_turn=per_turn))


class Scripted:
    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.answers.pop(0)


def test_table_talk_is_off_by_default():
    state = new_game(seed=1, player_count=4)
    assert state.economy.talks_per_turn == 0
    assert not any(n.startswith("talk:") for n in negotiations(state))
    with pytest.raises(IllegalAction):
        apply(state, "talk:1")


def test_a_player_may_speak_to_each_active_rival_at_the_start_of_its_turn():
    state = talking(players=3)
    players = list(state.players)
    players[2] = replace(players[2], out=True)
    assert [n for n in negotiations(replace(state, players=tuple(players))) if n.startswith("talk:")] == ["talk:1"]
    assert [n for n in negotiations(state) if n.startswith("talk:")] == ["talk:1", "talk:2"]


def test_the_rival_spoken_to_must_answer_then_the_turn_goes_on():
    state, events = apply(talking(), "talk:2")
    assert (state.pending, actor(state), legal_actions(state), negotiations(state)) == ("talk", 2, ("reply",), ("reply",))
    assert [(e.kind, e.player, dict(e.data)) for e in events] == [("talked", 0, {"to": 2})]
    state, events = apply(state, "reply")
    assert (state.pending, actor(state)) == ("roll", 0)
    assert [(e.kind, e.player, dict(e.data)) for e in events] == [("replied", 2, {"to": 0})]


def test_at_most_the_rules_number_of_talks_per_turn_and_a_new_turn_gives_them_back():
    state = talking(per_turn=2)
    for _ in range(2):
        state, _ = apply(apply(state, "talk:1")[0], "reply")
    assert not any(n.startswith("talk:") for n in negotiations(state))
    with pytest.raises(IllegalAction):
        apply(state, "talk:1")
    assert any(n.startswith("talk:") for n in negotiations(end_turn(state)))


@pytest.mark.parametrize("action", ["talk:0", "talk:7", "talk:x", "reply"])
def test_no_talk_to_oneself_nor_to_nobody_and_no_reply_without_a_question(action):
    with pytest.raises(IllegalAction):
        apply(talking(), action)


@pytest.mark.parametrize("pending", ["buy", "talk"])
def test_no_talk_in_the_middle_of_another_question(pending):
    """Else the question would be lost: a talk ends on `roll`, so a purchase, or an answer, would never be asked."""
    state = replace(talking(), pending=pending, listener=1 if pending == "talk" else None)
    with pytest.raises(IllegalAction):
        apply(state, "talk:2")


def test_the_speaker_sees_one_line_per_rival_and_the_offer_text_does_not_change():
    plain = render(view(talking(per_turn=0), 0)).splitlines()
    lines = render(view(talking(), 0)).splitlines()
    assert "- `talk:1` -- speak to player 1; they answer before you go on" in lines
    assert "- `talk:2` -- speak to player 2; they answer before you go on" in lines
    assert [l for l in lines if not l.startswith("- `talk:")] == plain


def test_the_rival_spoken_to_is_asked_with_the_speakers_seat():
    state, _ = apply(talking(), "talk:2")
    text = render(view(state, 2))
    assert "Player 0 speaks to you: answer them in your message (question: `talk`)" in text and "- `reply`" in text


def test_a_command_player_is_asked_to_reply_never_answered_for():
    state, _ = apply(talking(), "talk:1")
    ai = Scripted('{"action": "reply", "message": "Maybe, what do you offer?"}')
    assert CommandPlayer(ai, seat=1)(state, legal_actions(state)) == ("reply", "Maybe, what do you offer?")
    assert len(ai.prompts) == 1


@pytest.mark.parametrize("action, state", [("talk:1", talking()), ("reply", apply(talking(), "talk:1")[0])])
def test_talking_or_replying_without_words_is_refused_and_asked_again(action, state):
    seat = actor(state)
    ai = Scripted(json.dumps({"action": action, "message": ""}), json.dumps({"action": action, "message": "Hello."}))
    assert CommandPlayer(ai, seat=seat)(state, legal_actions(state)) == (action, "Hello.")
    assert "needs words" in ai.prompts[1]


def test_computers_never_talk_even_when_the_table_allows_it():
    state = new_game(seed=2, player_count=4)
    state = replace(state, economy=replace(state.economy, talks_per_turn=2, rounds=8))
    _, timed = play_game_rounds(state, [COMPUTERS[name] for name in ("easy", "normal", "hard", "adaptive")])
    assert not any(event.kind in ("talked", "replied") for _, event in timed)


def test_an_ai_table_with_talk_records_the_dialogue_and_replays_it(tmp_path):
    script = tmp_path / "talker.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "if '(question: `talk`)' in prompt:\n"
        "    heard = re.findall(r'said: \"([^\"]*)\"', prompt)\n"
        "    print(json.dumps({'action': 'reply', 'message': 'I heard: ' + heard[-1]}))\n"
        "elif '(question: `roll`)' in prompt and '- `talk:1` --' in prompt and 'Round 1 ' in prompt:\n"
        "    print(json.dumps({'action': 'talk:1', 'message': 'Shall we trade?'}))\n"
        "else:\n"
        "    print(json.dumps({'action': 'pass' if 'pass' in choices else choices[0], 'message': ''}))\n",
        encoding="utf-8")
    report = play_ai_game(("claude", "claude"), rounds=2, log_path=tmp_path / "talk.json", talks_per_turn=2,
                          commands={"claude": [sys.executable, str(script)]})
    kinds = [(e["kind"], e["player"]) for e in report["events"] if e["kind"] in ("said", "talked", "replied")]
    assert kinds[:4] == [("said", 0), ("talked", 0), ("said", 1), ("replied", 1)]
    said = [e["data"]["text"] for e in report["events"] if e["kind"] == "said"]
    assert said[:2] == ["Shall we trade?", "I heard: Shall we trade?"]
    assert report["talks_per_turn"] == 2 and report["fallbacks"] == 0
    decisions, _, _ = replay(report)
    assert [d.action for d in decisions if d.action in ("talk:1", "reply")][:2] == ["talk:1", "reply"]


def test_an_ai_table_refuses_a_negative_number_of_talks(tmp_path):
    with pytest.raises(ValueError, match="talk"):
        play_ai_game(("normal", "normal"), log_path=tmp_path / "never.json", talks_per_turn=-1)
    assert not (tmp_path / "never.json").exists()
