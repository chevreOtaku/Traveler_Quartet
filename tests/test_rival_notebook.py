"""The per-rival NOTEBOOK (plan step 8, P-TQ21): an AI player keeps private notes on each rival, rewrites them when it
wants, an empty note forgets; a cap per note forces the choice -- what is cut is COUNTED as forced forgetting. Every
version is journaled (the game forgets for it, the journal does not). Off by default."""

import json

from factory import game
from traveler_quartet.players.command_player import CommandPlayer, parse_answer, parse_reply


def _player(replies, cap=200, seat=0, history=None):
    prompts, queue = [], list(replies)

    def ask(prompt):
        prompts.append(prompt)
        return json.dumps(queue.pop(0)) if queue else '{"action": "roll"}'
    return CommandPlayer(ask, seat=seat, notebook_cap=cap, history=history), prompts


def _decide(player, times=1):
    for _ in range(times):
        player(game(players=3), ("roll", "build:1"))


def test_an_answer_with_nested_notes_is_still_read():
    text = 'ok {"action": "roll", "message": "hi", "notes": {"1": "refused twice"}} done'
    assert parse_answer(text) == ("roll", "hi") and parse_reply(text)["notes"] == {"1": "refused twice"}


def test_a_note_is_shown_at_the_next_decision_and_kept_until_rewritten():
    player, prompts = _player([{"action": "roll", "notes": {"1": "refuses under 1.5x"}}, {"action": "roll"}])
    _decide(player, 3)
    assert "refuses under 1.5x" not in prompts[0]
    assert "player 1: refuses under 1.5x" in prompts[1] and "player 1: refuses under 1.5x" in prompts[2]


def test_rewriting_replaces_and_an_empty_note_forgets():
    player, prompts = _player([{"action": "roll", "notes": {"1": "old", "2": "keep"}},
                               {"action": "roll", "notes": {"1": "new"}}, {"action": "roll", "notes": {"2": ""}}])
    _decide(player, 4)
    assert "player 1: new" in prompts[2] and "player 1: old" not in prompts[2]
    assert "player 2: keep" in prompts[2] and "player 2: keep" not in prompts[3]
    assert player.notes == {"1": "new"}


def test_only_rivals_get_notes_not_myself_nor_unknown_seats():
    player, _ = _player([{"action": "roll", "notes": {"0": "me", "7": "ghost", "x": "?", "2": "real"}}])
    _decide(player)
    assert player.notes == {"2": "real"}


def test_the_cap_cuts_and_the_cut_is_counted_as_forced_forgetting():
    player, _ = _player([{"action": "roll", "notes": {"1": "a" * 250}}], cap=200)
    _decide(player)
    assert len(player.notes["1"]) == 200 and player.log[-1]["notes_cut"] == 50


def test_every_version_of_the_notebook_is_journaled():
    player, _ = _player([{"action": "roll", "notes": {"1": "v1"}}, {"action": "roll", "notes": {"1": "v2"}}])
    _decide(player, 2)
    assert [d["notes"] for d in player.log] == [{"1": "v1"}, {"1": "v2"}]


def test_one_players_notes_never_reach_another_player():
    history = []
    first, _ = _player([{"action": "roll", "notes": {"1": "secret judgment"}}], seat=0, history=lambda: history)
    second, prompts = _player([], seat=1, history=lambda: history)
    _decide(first)
    second(game(players=3), ("roll", "build:1"))
    assert "secret judgment" not in prompts[0]


def test_an_ai_game_with_a_notebook_journals_the_notes(tmp_path):
    import sys
    from traveler_quartet.__main__ import build_parser
    from traveler_quartet.match.ai_game import play_ai_game
    script = tmp_path / "player.py"
    script.write_text("import json, re, sys\nprompt = sys.stdin.read()\n"
                      "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
                      "print(json.dumps({'action': choices[0], 'notes': {'1': 'watching you'}}))\n", encoding="utf-8")
    report = play_ai_game(("claude", "normal"), seed=1, rounds=2, log_path=tmp_path / "m.json",
                          commands={"claude": [sys.executable, str(script)]}, notebook_cap=50)
    assert report["ai_decisions"]["0"][-1]["notes"] == {"1": "watching you"}
    assert build_parser().parse_args(["ai-game", "--notebook-cap", "120"]).notebook_cap == 120


def test_without_a_notebook_nothing_changes():
    prompts = []
    player = CommandPlayer(lambda p: prompts.append(p) or '{"action": "roll", "notes": {"1": "x"}}', seat=0)
    player(game(), ("roll", "build:1"))
    assert "notes" not in prompts[0] and "notes" not in player.log[-1]
