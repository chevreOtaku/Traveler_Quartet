"""An AI game rebuilt from its report: the same events one by one, the state at each AI decision, or a refusal."""

import copy
import sys

import pytest

from traveler_quartet.match.ai_game import play_ai_game
from traveler_quartet.match.replay import ReplayMismatch, replay
from traveler_quartet.rules.engine import apply


@pytest.fixture
def talker(tmp_path):
    script = tmp_path / "talker.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "action = 'pass' if 'pass' in choices else choices[-1]\n"
        "message = 'I pass on this one.' if action == 'pass' else ''\n"
        "print(json.dumps({'action': action, 'message': message}))\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


@pytest.fixture
def report(tmp_path, talker):
    return play_ai_game(("claude", "normal", "codex", "easy"), seed=5, rounds=6, log_path=tmp_path / "game.json",
                        commands={"claude": talker, "codex": talker})


def test_the_replay_gives_back_every_ai_decision_with_its_state_and_message(report):
    decisions, timed, final = replay(report)
    for seat in (0, 2):
        mine = [d for d in decisions if d.seat == seat]
        assert [d.action for d in mine] == [d["action"] for d in report["ai_decisions"][str(seat)]]
        spoken = [e for e in report["events"] if e["kind"] == "said" and e["player"] == seat]
        assert spoken and sum(1 for d in mine if d.message) == len(spoken)
    for decision in decisions:
        apply(decision.state, decision.action)
        assert decision.state.pending is not None
    assert final.over and len(timed) == len(report["events"])


def test_a_forced_move_is_played_without_using_a_logged_decision(tmp_path):
    """An AI seat with ONE legal move and nothing to negotiate is not asked (the command player plays it): the replay
    must not spend a logged decision there. A spender runs out of gold, and auctions leave it only `drop`."""
    script = tmp_path / "spender.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "raises = sorted((c for c in choices if c.startswith('raise:')), key=lambda c: -int(c.split(':')[1]))\n"
        "pick = 'buy' if 'buy' in choices else raises[0] if raises else choices[0]\n"
        "print(json.dumps({'action': pick, 'message': 'all in'}))\n",
        encoding="utf-8",
    )
    report = play_ai_game(("claude", "normal"), seed=2, rounds=30, log_path=tmp_path / "spender.json",
                          commands={"claude": [sys.executable, str(script)]})
    decisions, timed, _ = replay(report)
    asked = len(report["ai_decisions"]["0"])
    played = sum(1 for _, e in timed if e.player == 0 and e.kind in ("dropped", "raised", "bought", "declined"))
    assert len(decisions) == asked and played > 0


def test_a_message_goes_to_its_own_move_when_the_same_move_is_made_twice_in_a_round(tmp_path):
    """Found on a real game (13/11): two `raise:10` in one auction, the first silent, the second with a message --
    matched by round and action, the message went to the first one."""
    counter = tmp_path / "calls.txt"
    script = tmp_path / "every_other.py"
    script.write_text(
        "import json, pathlib, re, sys\n"
        f"counter = pathlib.Path(r'{counter}')\n"
        "calls = int(counter.read_text()) + 1 if counter.exists() else 1\n"
        "counter.write_text(str(calls))\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "raises = [c for c in choices if c.startswith('raise:')]\n"
        "pick = 'pass' if 'pass' in choices else raises[0] if raises else choices[0]\n"
        "print(json.dumps({'action': pick, 'message': 'call %d' % calls if calls % 2 == 0 else ''}))\n",
        encoding="utf-8",
    )
    report = play_ai_game(("claude", "normal", "normal", "normal"), seed=3, rounds=20, log_path=tmp_path / "g.json",
                          commands={"claude": [sys.executable, str(script)]})
    decisions, _, _ = replay(report)
    silent_then_spoken = [(a, b) for a in decisions for b in decisions
                          if a.rank + 1 == b.rank and (a.state.round, a.action) == (b.state.round, b.action)
                          and a.message is None and b.message]
    assert silent_then_spoken, "the witness: the same move twice in a round, silent first, then spoken"


def test_a_damaged_event_is_refused(report):
    damaged = copy.deepcopy(report)
    built = next(e for e in damaged["events"] if e["kind"] == "rolled")
    built["player"] = (built["player"] + 1) % 4
    with pytest.raises(ReplayMismatch, match="event"):
        replay(damaged)


def test_a_changed_decision_is_refused(report):
    changed = copy.deepcopy(report)
    changed["ai_decisions"]["0"][0]["action"] = "build:39"
    with pytest.raises(ReplayMismatch):
        replay(changed)


def test_a_missing_decision_is_refused(report):
    short = copy.deepcopy(report)
    short["ai_decisions"]["2"].pop()
    with pytest.raises(ReplayMismatch):
        replay(short)
