"""The say against the do: statements read by a model, verdicts given by the replayed engine."""

import json
import sys

import pytest

from traveler_quartet.match.ai_game import play_ai_game
from traveler_quartet.match.replay import replay
from traveler_quartet.match.talk import (CONTRADICTED, SUPPORTED, UNDETERMINABLE, Statement, judge,
                                         parse_statements, verdict)


@pytest.fixture(scope="module")
def game(tmp_path_factory):
    script = tmp_path_factory.mktemp("talker") / "talker.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "action = 'pass' if 'pass' in choices else choices[-1]\n"
        "message = 'I pass on this one.' if action == 'pass' else ''\n"
        "print(json.dumps({'action': action, 'message': message}))\n",
        encoding="utf-8",
    )
    target = tmp_path_factory.mktemp("logs") / "game.json"
    report = play_ai_game(("claude", "normal", "normal", "normal"), seed=5, rounds=12, log_path=target,
                          commands={"claude": [sys.executable, str(script)]})
    decisions, _, _ = replay(report)
    return report, decisions


def _passes(decisions):
    return [d for d in decisions if d.action == "pass"]


def _later(decisions, decision):
    return [d for d in decisions if d.seat == decision.seat and d.rank > decision.rank]


def test_an_announce_is_checked_against_the_move_it_goes_with(game):
    _, decisions = game
    passing = _passes(decisions)[0]
    assert verdict(Statement("A", "I pass", "pass"), passing, []) == SUPPORTED
    assert verdict(Statement("A", "I buy it", "buy"), passing, []) == CONTRADICTED
    assert verdict(Statement("A", "I won't pass", "pass", negated=True), passing, []) == CONTRADICTED
    assert verdict(Statement("A", "I am rich", "other"), passing, []) == UNDETERMINABLE
    assert verdict(Statement("A", "I build in Atlantis", "build", town="atlantis"), passing, []) == UNDETERMINABLE


def test_a_claim_is_checked_against_the_state_at_that_moment(game):
    _, decisions = game
    decision = next(d for d in decisions if any(o is not None for o in d.state.owners))
    square = next(i for i, owner in enumerate(decision.state.owners) if owner is not None)
    owner = decision.state.owners[square]
    other = (owner + 1) % len(decision.state.players)
    cash = decision.state.players[owner].cash
    assert verdict(Statement("E", "", "own", square=square, player=owner), decision, []) == SUPPORTED
    assert verdict(Statement("E", "", "own", square=square, player=other), decision, []) == CONTRADICTED
    assert verdict(Statement("E", "", "cash", player=owner, amount=cash), decision, []) == SUPPORTED
    assert verdict(Statement("E", "", "cash", player=owner, amount=cash + 500), decision, []) == CONTRADICTED
    assert verdict(Statement("E", "", "own", town="atlantis", player=owner), decision, []) == UNDETERMINABLE


@pytest.fixture(scope="module")
def buyer(tmp_path_factory):
    script = tmp_path_factory.mktemp("buyer") / "buyer.py"
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        "choices = re.findall(r'^- `([^`]+)`$', prompt, re.MULTILINE)\n"
        "print(json.dumps({'action': 'buy' if 'buy' in choices else choices[0], 'message': 'mine!'}))\n",
        encoding="utf-8",
    )
    report = play_ai_game(("claude", "normal"), seed=2, rounds=15, log_path=tmp_path_factory.mktemp("b") / "b.json",
                          commands={"claude": [sys.executable, str(script)]})
    decisions, _, _ = replay(report)
    return decisions


def test_a_claim_said_with_a_move_may_speak_of_the_state_that_move_makes(buyer):
    """v2 (13/11): « Bards' Corner is mine! » said WITH `buy` was judged on the state BEFORE the purchase."""
    purchase = next(d for d in buyer if d.action == "buy")
    square = purchase.state.players[purchase.seat].position
    assert purchase.state.owners[square] is None
    assert verdict(Statement("E", "it is mine", "own", square=square), purchase, []) == SUPPORTED
    assert verdict(Statement("E", "it is not mine", "own", square=square, negated=True), purchase, []) == SUPPORTED
    other = next(i for i, sq in enumerate(purchase.state.board.squares) if sq.town and i != square
                 and purchase.state.owners[i] is None)
    assert verdict(Statement("E", "that one is mine", "own", square=other), purchase, []) == CONTRADICTED


def test_a_claim_on_how_many_districts_of_a_town_is_counted(buyer):
    """v2 (13/11): « two of three in orange » was read as « all of orange »."""
    decision = next(d for d in reversed(buyer) if any(o == d.seat for o in d.state.owners))
    town, squares = next((t, s) for t, s in decision.state.board.towns.items()
                         if any(decision.state.owners[i] == decision.seat for i in s))
    count = sum(1 for i in squares if decision.state.owners[i] == decision.seat)
    assert verdict(Statement("E", "", "own", town=town, amount=count), decision, []) == SUPPORTED
    assert verdict(Statement("E", "", "own", town=town, amount=count + 2), decision, []) == CONTRADICTED


def test_the_extractor_is_told_what_each_verb_means_in_this_game(game):
    from traveler_quartet.match.talk import extraction_prompt

    _, decisions = game
    prompt = extraction_prompt(next(d for d in decisions if d.message))
    assert "sell = sell a BUILDING" in prompt and "selling or buying a district between players for gold is an offer" in prompt


def test_a_promise_is_contradicted_only_when_the_move_was_possible_and_not_played(game):
    _, decisions = game
    first = _passes(decisions)[0]
    later = _later(decisions, first)
    assert any(d.action == "pass" for d in later), "the scripted player passes again later"
    assert verdict(Statement("P", "I'll buy the next one", "buy"), first, later) == CONTRADICTED
    assert verdict(Statement("P", "I won't buy anything", "buy", negated=True), first, later) == SUPPORTED
    assert verdict(Statement("P", "I will pass again", "pass"), first, later) == SUPPORTED
    assert verdict(Statement("P", "next turn I buy", "buy", horizon_rounds=0), decisions[-1], []) == UNDETERMINABLE
    assert verdict(Statement("P", "I won't buy", "buy", negated=True, horizon_rounds=0), decisions[-1], []) == UNDETERMINABLE


def test_the_extractor_answer_is_read_strictly():
    text = ('noise {"statements": [{"class": "A", "quote": "I pass", "verb": "pass", "square": true}, '
            '{"class": "O", "verb": "other"}, {"class": "P", "verb": 3}, {"class": "E", "verb": "cash", "amount": 300}]}')
    parsed = parse_statements(text)
    assert [(s.kind, s.verb, s.square, s.amount) for s in parsed] == [("A", "pass", None, None), ("E", "cash", None, 300)]
    assert parse_statements("no json at all") == [] and parse_statements("{broken") == []


def test_judge_log_writes_the_verdicts_outside_every_repository(game, tmp_path):
    from traveler_quartet.match.talk import judge_log

    report, _ = game
    source = tmp_path / "report.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    extractor = tmp_path / "extractor.py"
    extractor.write_text("import json, sys\nsys.stdin.read()\nprint(json.dumps({'statements': [{'class': 'A', "
                         "'quote': 'I pass', 'verb': 'pass'}]}))\n", encoding="utf-8")
    command = [sys.executable, str(extractor)]
    result = judge_log(source, tmp_path / "verdicts.json", command=command)
    assert json.loads((tmp_path / "verdicts.json").read_text(encoding="utf-8")) == json.loads(json.dumps(result))
    assert result["summary"]["A"][SUPPORTED] == result["messages"] > 0
    repo = tmp_path / "repository"
    (repo / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="outside"):
        judge_log(source, repo / "verdicts.json", command=command)


def test_judge_reads_every_message_and_counts_the_verdicts(game):
    report, decisions = game
    answer = json.dumps({"statements": [{"class": "A", "quote": "I pass", "verb": "pass", "negated": False}]})
    prompts = []
    result = judge(report, lambda prompt: prompts.append(prompt) or answer)
    spoken = sum(1 for e in report["events"] if e["kind"] == "said")
    assert result["messages"] == spoken == len(prompts) > 0
    assert result["summary"] == {"A": {SUPPORTED: spoken, CONTRADICTED: 0, UNDETERMINABLE: 0}}
    assert set(result["by_speaker"]) == {"claude"}
    assert all(row["speaker"] == "claude" and row["player"] is None for row in result["statements"])
    assert all("I pass on this one." in p and "happened before or after" in p for p in prompts)
    assert len(set(prompts)) == 1, "the same message at another moment of the game: the same prompt -- no state leaks"
