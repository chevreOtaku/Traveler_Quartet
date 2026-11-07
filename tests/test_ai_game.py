import json
import os
import subprocess
import sys

import pytest

from traveler_quartet.match.ai_game import play_ai_game


@pytest.fixture
def fake_command(tmp_path):
    script = tmp_path / "player.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "action = 'pass' if 'pass' in choices else choices[0]\n"
        "print(json.dumps({'action': action, 'message': 'A scripted decision.'}))\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


def test_a_real_command_plays_a_short_game_and_writes_its_report(tmp_path, fake_command):
    target = tmp_path / "match.json"
    report = play_ai_game(("claude", "normal"), seed=1, rounds=2, log_path=target,
                          commands={"claude": fake_command})

    assert json.loads(target.read_text(encoding="utf-8")) == report
    assert report["over"] is True and report["rounds_limit"] == 2
    assert report["rounds_played"] <= 2
    assert report["seats"] == ["claude", "normal"]
    assert {row["seat"] for row in report["ranking"]} == {0, 1}
    assert report["ai_decisions"]["0"]
    assert report["said"] and all(event["player"] == 0 for event in report["said"])
    assert report["fallbacks"] == 0 and report["illegal_then_corrected"] == 0
    assert len(report["actions_by_seat"]) == 2 and report["minutes"] >= 0


def test_an_ai_seat_reads_what_happened_since_its_last_decision(tmp_path, fake_command):
    report = play_ai_game(("claude", "normal"), seed=1, rounds=3, log_path=tmp_path / "match.json",
                          commands={"claude": fake_command})
    sizes = [d["summary_chars"] for d in report["ai_decisions"]["0"]]
    assert sizes and all(size > 0 for size in sizes)


@pytest.mark.parametrize("seats", [("unknown", "normal"), ("normal",), ("easy",) * 5])
def test_invalid_seats_are_refused_before_a_command_runs(seats, tmp_path):
    with pytest.raises(ValueError, match="seat|players"):
        play_ai_game(seats, log_path=tmp_path / "never.json")
    assert not (tmp_path / "never.json").exists()


@pytest.mark.parametrize("rounds", [0, -1])
def test_nonpositive_rounds_are_refused(rounds, tmp_path):
    with pytest.raises(ValueError, match="rounds"):
        play_ai_game(("easy", "normal"), rounds=rounds, log_path=tmp_path / "never.json")


def test_logs_cannot_be_written_inside_a_repository(tmp_path):
    repo = tmp_path / "repository"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    target = repo / "nested" / "match.json"
    with pytest.raises(ValueError, match="outside"):
        play_ai_game(("easy", "normal"), rounds=1, log_path=target)
    assert not target.exists()


def test_an_existing_log_is_not_overwritten(tmp_path):
    target = tmp_path / "match.json"
    target.write_text("original", encoding="utf-8")
    with pytest.raises(FileExistsError):
        play_ai_game(("easy", "normal"), rounds=1, log_path=target)
    assert target.read_text(encoding="utf-8") == "original"


def test_the_cli_runs_bots_without_calling_an_ai(tmp_path):
    target = tmp_path / "cli.json"
    result = subprocess.run(
        [sys.executable, "-m", "traveler_quartet", "ai-game", "--seats", "easy,normal",
         "--rounds", "1", "--log", str(target)],
        capture_output=True, text=True, env=os.environ.copy(), timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["log_path"] == str(target)
    assert json.loads(target.read_text(encoding="utf-8"))["rounds_limit"] == 1


def test_both_ai_seats_get_their_own_decision_journals(tmp_path, fake_command):
    report = play_ai_game(("claude", "codex", "normal", "normal"), rounds=1,
                          log_path=tmp_path / "both.json",
                          commands={"claude": fake_command, "codex": fake_command})
    assert set(report["ai_decisions"]) == {"0", "1"}
    assert all(report["ai_decisions"].values())
    assert {event["player"] for event in report["said"]} == {0, 1}


def test_default_rounds_stay_at_thirty_and_default_log_is_external(tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    report = play_ai_game(("easy", "normal"))
    assert report["rounds_limit"] == 30
    assert os.path.dirname(report["log_path"]) == str(tmp_path)
    assert report["ai_decisions"] == {} and report["said"] == []


@pytest.mark.parametrize("failure", ["raise SystemExit(7)", "print('   '); raise SystemExit(0)"])
def test_an_agent_failure_preserves_the_partial_game(tmp_path, fake_command, failure):
    script = tmp_path / "player.py"
    source = script.read_text(encoding="utf-8")
    source = source.replace("choices =", "if '# Round 2 /' in prompt:\n    " + failure + "\nchoices =")
    script.write_text(source, encoding="utf-8")
    target = tmp_path / "interrupted.json"

    with pytest.raises(RuntimeError, match="interrupted.*interrupted.json"):
        play_ai_game(("claude", "normal"), seed=1, rounds=10, log_path=target,
                     commands={"claude": fake_command})

    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["status"] == "interrupted" and report["over"] is False
    assert report["error"]["round"] == 2 and report["error"]["seat"] == 0
    assert report["error"]["type"] in ("CalledProcessError", "RuntimeError")
    assert report["ai_decisions"]["0"] and report["said"]
    assert all(event["round"] == 1 for event in report["said"])
    assert report["ranking_is_final"] is False and report["minutes"] >= 0


def test_cli_exits_nonzero_after_saving_a_partial_log(tmp_path):
    project = tmp_path / "driver.py"
    project.write_text(
        "import sys\nfrom traveler_quartet import __main__ as cli\n"
        "from traveler_quartet.match import ai_game\n"
        "ai_game.COMMANDS['codex'] = [sys.executable, '-c', 'raise SystemExit(7)']\n"
        "raise SystemExit(cli.main(sys.argv[1:]))\n", encoding="utf-8")
    target = tmp_path / "cli-interrupted.json"
    result = subprocess.run([sys.executable, str(project), "ai-game", "--seats", "codex,normal",
                             "--rounds", "2", "--log", str(target)],
                            capture_output=True, text=True, env=os.environ.copy(), timeout=30)
    assert result.returncode == 2
    assert "interrupted" in result.stderr and str(target) in result.stderr
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["error"]["seat"] == 0 and report["error"]["round"] == 1
