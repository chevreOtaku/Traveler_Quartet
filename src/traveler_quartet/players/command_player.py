"""An AI player BY COMMAND (step 9, D44): the state text goes to an AI agent run from the command line (for example
`claude -p` or `codex exec`, on the user's own subscription), the answer comes back as JSON `{"action", "message"}`.

- Only REAL choices are asked: one legal action and nothing to negotiate -> it is played without asking.
- An illegal answer is refused and asked again, with the reason ; after `retries`, a SAFE action is played and logged.
- The agent sees only `render(view(state, seat))` -- never the decks order nor the seed -- and, given a `history`, the
  public events since ITS last decision (`players/recent.py`, plan step 7): a cursor moves at each decision it answers.
- `run_command` runs the agent in an EMPTY temporary folder, outside every repository, its code-running tools off.
"""

import json
import re
import shutil
import subprocess
import tempfile
import time
from typing import Callable, List, Optional, Sequence, Tuple

from traveler_quartet.players.recent import TimedEvent, summary_lines
from traveler_quartet.players.text import render
from traveler_quartet.players.view import view
from traveler_quartet.rules.engine import GameState, IllegalAction, apply, negotiations

ANSWER_FORMAT = ('Answer with ONE JSON object and nothing else: {"action": "<one of your choices, or a full offer>", '
                 '"message": "<what you say to the table, may be empty>"}')
INTRO = ("You are playing Traveler Quartet, a board game for 2-4 merchants. The richest player after the last round "
         "wins: cash plus the value of districts and buildings.")
SAFE = ("pass", "drop", "refuse", "stay", "roll", "bid:0", "bankrupt")
JSON_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)
# Claude as a LEAN player (measured 06/11): the full Claude Code agent resent its whole instructions and tool list at each
# move -- ~25 000 input tokens for a ~160-token game question. A short system prompt and NO tools: ~900 tokens, the same
# decision, a quarter of the cost, half the time; and with no tools it can read or write nothing at all.
PLAYER_SYSTEM_PROMPT = ("You are a player in a board game. Read the state and answer with the JSON object asked for, "
                        "nothing else.")
CLAUDE = ["claude", "-p", "--restricted", "--strict-mcp-config", "--output-format", "text",
          "--system-prompt", PLAYER_SYSTEM_PROMPT, "--tools", ""]
# Codex (its developer reference, read 06/11): read-only sandbox, run outside a git repository, nothing persisted,
# the prompt on stdin ("-"). To be tried once Codex is installed and logged in.
CODEX = ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "-"]


def parse_answer(text: str) -> Optional[Tuple[str, str]]:
    for match in JSON_OBJECT.finditer(text):
        try:
            data = json.loads(match.group(0))
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("action"), str):
            return data["action"].strip(), str(data.get("message") or "")
    return None


def _legal(state: GameState, action: str) -> bool:
    try:
        apply(state, action)
    except IllegalAction:
        return False
    return True


def _safe(legal: Sequence[str]) -> str:
    return next((a for a in SAFE if a in legal), legal[0])


class CommandPlayer:
    """A chooser for the runner: `(state, legal) -> (action, message)`. `ask(prompt) -> text` is the AI."""

    def __init__(self, ask: Callable[[str], str], seat: int, retries: int = 2,
                 history: Optional[Callable[[], Sequence[TimedEvent]]] = None):
        self.ask, self.seat, self.retries, self.log = ask, seat, retries, []
        self.history, self.cursor = history, 0

    def negotiable(self, state: GameState) -> bool:
        return bool(negotiations(state))

    def _summary(self, state: GameState) -> str:
        if self.history is None:
            return ""
        names = [square.name for square in state.board.squares]
        lines = summary_lines(list(self.history())[self.cursor:], state.catalog, names, self.seat)
        return "\n\n## Since your last decision\n" + ("\n".join(lines) if lines else "- nothing happened")

    def __call__(self, state: GameState, legal: Tuple[str, ...]) -> Tuple[str, Optional[str]]:
        if len(legal) == 1 and not self.negotiable(state):
            return legal[0], None
        summary = self._summary(state)
        prompt, started = f"{INTRO}\n\n{render(view(state, self.seat))}{summary}\n\n{ANSWER_FORMAT}", time.time()
        sizes = {"prompt_chars": len(prompt), "summary_chars": len(summary)}
        if self.history is not None:
            self.cursor = len(self.history())
        for attempt in range(1, self.retries + 2):
            answer = parse_answer(self.ask(prompt))
            if answer and _legal(state, answer[0]):
                self._note(state, attempt, answer[0], False, started, sizes)
                return answer[0], answer[1] or None
            said = answer[0] if answer else "no JSON answer"
            prompt += f"\n\nYour answer `{said}` is not legal now. Choose again. {ANSWER_FORMAT}"
        action = _safe(legal)
        self._note(state, attempt, action, True, started, sizes)
        return action, None

    def _note(self, state: GameState, attempts: int, action: str, fallback: bool, started: float, sizes: dict) -> None:
        self.log.append({"round": state.round, "question": state.pending, "attempts": attempts, "action": action,
                         "fallback": fallback, "seconds": round(time.time() - started, 1), **sizes})


def run_command(command: List[str], timeout: float = 300.0) -> Callable[[str], str]:
    """`ask` for a command-line agent: the prompt on its standard input, run in an EMPTY temporary folder."""
    program = shutil.which(command[0])
    if program is None:
        raise FileNotFoundError(f"{command[0]!r} is not installed (or not on the PATH)")
    full = [program] + list(command[1:])

    def ask(prompt: str) -> str:
        with tempfile.TemporaryDirectory(prefix="tq-player-") as empty:
            done = subprocess.run(full, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  cwd=empty, timeout=timeout)
        done.check_returncode()
        if not done.stdout.strip():
            raise RuntimeError("agent command returned an empty answer")
        return done.stdout
    return ask
