"""An AI player BY COMMAND (step 9, D44): it gives the state text to a command (an AI agent run from the command line),
reads a JSON answer, refuses an illegal action and asks again -- and never asks when there is no real choice. The
command is injected here: no agent runs in the tests."""

from factory import game, own
from traveler_quartet.players.command_player import ANSWER_FORMAT, CommandPlayer, parse_answer
from traveler_quartet.rules.engine import apply, legal_actions


class Scripted:
    """A fake AI: answers from a list, and records the prompts it was given."""

    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answers.pop(0)


def _buy_question():
    state, _ = apply(game(seed=3), "roll")
    while state.pending != "buy":
        state, _ = apply(game(seed=state.seed + 1), "roll")
    return state


def test_the_answer_is_read_from_the_json_even_with_words_around_it():
    assert parse_answer('Sure. {"action": "buy", "message": "mine now"} done') == ("buy", "mine now")
    assert parse_answer("no json here") is None


def test_no_question_is_asked_when_there_is_only_one_thing_to_do():
    from factory import cash
    state, _ = apply(_buy_question(), "pass")
    bidder = state.auction.bidders[state.auction.turn]
    state = cash(state, bidder, 0)
    assert legal_actions(state) == ("drop",)
    ai = Scripted()
    assert CommandPlayer(ai, seat=bidder)(state, legal_actions(state)) == ("drop", None) and ai.prompts == []


def test_a_legal_answer_is_played_with_its_message():
    state = _buy_question()
    ai = Scripted('{"action": "buy", "message": "a fine street"}')
    assert CommandPlayer(ai, seat=state.current)(state, legal_actions(state)) == ("buy", "a fine street")


def test_an_illegal_answer_is_refused_and_asked_again_with_the_reason():
    state = _buy_question()
    ai = Scripted('{"action": "fly", "message": ""}', '{"action": "pass", "message": "too dear"}')
    assert CommandPlayer(ai, seat=state.current)(state, legal_actions(state)) == ("pass", "too dear")
    assert "fly" in ai.prompts[1] and "not legal" in ai.prompts[1]


def test_after_too_many_wrong_answers_a_safe_action_is_played_and_logged():
    state = _buy_question()
    ai = Scripted(*['{"action": "fly"}'] * 3)
    player = CommandPlayer(ai, seat=state.current, retries=2)
    assert player(state, legal_actions(state)) == ("pass", None)
    assert player.log[-1]["fallback"] is True and player.log[-1]["attempts"] == 3 and len(ai.prompts) == 3


def test_a_trade_contract_is_accepted_when_the_engine_accepts_it():
    state = own(own(game(players=2), 0, 1), 1, 3)
    ai = Scripted('{"action": "offer:1:40:::0:3:", "message": "deal?"}')
    assert CommandPlayer(ai, seat=0)(state, legal_actions(state)) == ("offer:1:40:::0:3:", "deal?")


def test_the_prompt_is_the_players_view_and_the_answer_format_never_the_future():
    state = _buy_question()
    ai = Scripted('{"action": "buy", "message": ""}')
    CommandPlayer(ai, seat=state.current)(state, legal_actions(state))
    assert ANSWER_FORMAT in ai.prompts[0] and "Your choices" in ai.prompts[0] and "seed" not in ai.prompts[0]


def test_the_agents_are_run_with_their_safeguards_never_with_them_off():
    from traveler_quartet.players.command_player import CLAUDE, CODEX
    assert "--restricted" in CLAUDE and "--strict-mcp-config" in CLAUDE
    assert CODEX[CODEX.index("--sandbox") + 1] == "read-only"
    assert not any("dangerously" in flag or flag in ("--yolo", "danger-full-access") for flag in CLAUDE + CODEX)


def test_a_failed_agent_command_cannot_be_mistaken_for_a_valid_decision(tmp_path):
    import subprocess
    import sys
    import pytest
    from traveler_quartet.players.command_player import run_command
    script = tmp_path / "failed_agent.py"
    script.write_text('print(\'{"action":"roll"}\')\nraise SystemExit(7)\n', encoding="utf-8")
    with pytest.raises(subprocess.CalledProcessError):
        run_command([sys.executable, str(script)])("Choose an action")


def test_a_successful_but_empty_agent_command_is_an_explicit_error(tmp_path):
    import sys
    import pytest
    from traveler_quartet.players.command_player import run_command
    script = tmp_path / "empty_agent.py"
    script.write_text('print("   ")\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="empty"):
        run_command([sys.executable, str(script)])("Choose an action")
