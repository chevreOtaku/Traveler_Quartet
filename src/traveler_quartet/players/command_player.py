"""An AI player BY COMMAND (step 9, D44): the state text goes to an AI agent run from the command line (for example
`claude -p` or `codex exec`, on the user's own subscription), the answer comes back as JSON `{"action", "message"}`.

- Only REAL choices are asked: one legal action and nothing to negotiate -> it is played without asking.
- An illegal answer is refused and asked again, with the reason ; after `retries`, a SAFE action is played and logged.
- The agent sees only `render(view(state, seat))` -- never the decks order nor the seed -- and, given a `history`, the
  public events since ITS last decision (`players/recent.py`, plan step 7): a cursor moves at each decision it answers.
- `run_command` runs the agent in an EMPTY temporary folder, outside every repository, its code-running tools off.
"""

import json
import shutil
import subprocess
import tempfile
import time
from typing import Callable, List, Optional, Sequence, Tuple

from traveler_quartet.players.notebook import NOTES_FORMAT, notes_section, update_notes
from traveler_quartet.players.recent import TimedEvent, summary_lines
from traveler_quartet.players.text import OFFER_STYLES, render
from traveler_quartet.players.view import view
from traveler_quartet.rules.engine import GameState, IllegalAction, apply, negotiations

ANSWER_FORMAT = ('Answer with ONE JSON object and nothing else: {"action": "<one of your choices, or a full offer>", '
                 '"message": "<what you say to the table, may be empty>"}')
INTRO = ("You are playing Traveler Quartet, a board game for 2-4 merchants. The richest player after the last round "
         "wins: cash plus the value of districts and buildings.")
SAFE = ("pass", "drop", "refuse", "stay", "roll", "bid:0", "bankrupt")
WORDED = ("talk", "reply")
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


def parse_reply(text: str) -> Optional[dict]:
    """The first COMPLETE JSON object with an "action" -- nested objects included (the notebook's "notes")."""
    decoder = json.JSONDecoder()
    for start in (i for i, char in enumerate(text) if char == "{"):
        try:
            data, _ = decoder.raw_decode(text, start)
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("action"), str):
            return data
    return None


def parse_answer(text: str) -> Optional[Tuple[str, str]]:
    data = parse_reply(text)
    return (data["action"].strip(), str(data.get("message") or "")) if data else None


def _side(part) -> List[str]:
    """One side of a named offer -> its three contract fields. Strict: a wrong type is an error, never a guess."""
    part = {} if part is None else part
    gold, squares, cards = part.get("gold", 0), part.get("squares", []), part.get("cards", [])
    if type(gold) is not int or not isinstance(squares, list) or not isinstance(cards, list):
        raise TypeError("not a named offer")
    if any(type(i) is not int for i in squares) or any(not isinstance(c, str) or ":" in c or "," in c for c in cards):
        raise TypeError("not a named offer")
    return [str(gold), ",".join(str(i) for i in squares), ",".join(cards)]


def contract_action(reply: dict) -> Optional[str]:
    """An offer or counter-offer written with NAMED fields (the `named` style) -> the engine's contract, `offer:<player>:`
    or `counter:` then the six fields; None if `reply` is not one. The engine still decides whether it is legal."""
    kind = str(reply.get("action", "")).strip()
    if kind not in ("offer", "counter"):
        return None
    try:
        if kind == "offer" and type(reply.get("to")) is not int:
            return None
        head = f"offer:{reply['to']}" if kind == "offer" else "counter"
        return ":".join([head] + _side(reply.get("give")) + _side(reply.get("ask")))
    except (AttributeError, TypeError):
        return None


def _legal(state: GameState, action: str) -> bool:
    try:
        apply(state, action)
    except IllegalAction:
        return False
    return True


def _refusal(state: GameState, action: Optional[str], message: str) -> Optional[str]:
    """Why an answer cannot be played, or None. Speaking (`talk`) and answering (`reply`) need words."""
    if not action or not _legal(state, action):
        return f"Your answer `{action or 'no JSON answer'}` is not legal now. Choose again."
    if action.partition(":")[0] in WORDED and not message.strip():
        return f"Your answer `{action}` needs words: write what you say in \"message\"."
    return None


def _safe(legal: Sequence[str]) -> str:
    return next((a for a in SAFE if a in legal), legal[0])


class CommandPlayer:
    """A chooser for the runner: `(state, legal) -> (action, message)`. `ask(prompt) -> text` is the AI."""

    def __init__(self, ask: Callable[[str], str], seat: int, retries: int = 2,
                 history: Optional[Callable[[], Sequence[TimedEvent]]] = None, notebook_cap: Optional[int] = None,
                 offer_style: str = "fields"):
        if offer_style not in OFFER_STYLES:
            raise ValueError(f"unknown offer style {offer_style!r}; known: {', '.join(OFFER_STYLES)}")
        self.ask, self.seat, self.retries, self.log = ask, seat, retries, []
        self.history, self.cursor = history, 0
        self.notebook_cap, self.notes = notebook_cap, {}
        self.offer_style = offer_style

    def _action(self, reply: Optional[dict]) -> Optional[str]:
        """The action an answer plays: a named offer is translated only for a `named` seat (the others play as before)."""
        if not reply:
            return None
        named = contract_action(reply) if self.offer_style == "named" else None
        return named or reply["action"].strip()

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
        notebook = notes_section(self.notes, self.notebook_cap) if self.notebook_cap else ""
        answer_format = ANSWER_FORMAT + (NOTES_FORMAT if self.notebook_cap else "")
        prompt = f"{INTRO}\n\n{render(view(state, self.seat), self.offer_style)}{summary}{notebook}\n\n{answer_format}"
        started, sizes = time.time(), {"prompt_chars": len(prompt), "summary_chars": len(summary)}
        if self.history is not None:
            self.cursor = len(self.history())
        for attempt in range(1, self.retries + 2):
            reply = parse_reply(self.ask(prompt))
            action = self._action(reply)
            message = str(reply.get("message") or "") if reply else ""
            refusal = _refusal(state, action, message)
            if refusal is None:
                self._keep_notes(state, reply.get("notes"), sizes)
                self._note(state, attempt, action, False, started, sizes)
                return action, message or None
            prompt += f"\n\n{refusal} {answer_format}"
        action = _safe(legal)
        self._keep_notes(state, None, sizes)
        self._note(state, attempt, action, True, started, sizes)
        return action, None

    def _keep_notes(self, state: GameState, proposed, sizes: dict) -> None:
        if not self.notebook_cap:
            return
        self.notes, cut = update_notes(self.notes, proposed, self.seat, len(state.players), self.notebook_cap)
        sizes.update({"notes": dict(self.notes), "notes_cut": cut})

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
