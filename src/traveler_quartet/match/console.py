"""Playing in the CONSOLE (step 7): one human against computer players, through a game session (`session.py`).

The human is a remote seat like any other: he sees only HIS view (`render(view)`), the computers play between his turns,
every answer is checked by the engine. He types the NUMBER of a legal action, optionally followed by a message for the
table (« 2 good luck »); « o » builds a trade offer from simple questions (no format to type); « q » leaves.
`read` and `write` stand for the keyboard and the screen, so a test can script them.
"""

from typing import Callable, Dict, List, Optional, Sequence, Tuple

from traveler_quartet.match.session import REMOTE, act, events_for, new_session, seen
from traveler_quartet.rules.endgame import ranking
from traveler_quartet.rules.engine import IllegalAction

Read = Callable[[str], str]
Write = Callable[[str], None]
MAX_ANSWERS = 100_000


def parse_choice(text: str, legal: Sequence[str]) -> Optional[Tuple[str, Optional[str]]]:
    """« 2 good luck » -> (the 2nd legal action, "good luck") ; anything else -> None."""
    number, _, message = text.strip().partition(" ")
    if not number.isdigit() or not 1 <= int(number) <= len(legal):
        return None
    return legal[int(number) - 1], (message.strip() or None)


def build_offer(to: int, give_gold: int, give_squares: Sequence[int], give_cards: Sequence[str], ask_gold: int,
                ask_squares: Sequence[int], ask_cards: Sequence[str]) -> str:
    """The offer contract of the engine, built from plain values."""
    join = lambda items: ",".join(str(i) for i in items)
    return f"offer:{to}:{give_gold}:{join(give_squares)}:{join(give_cards)}:{ask_gold}:{join(ask_squares)}:{join(ask_cards)}"


def _numbers(text: str) -> List[int]:
    return [int(x) for x in text.replace(" ", "").split(",") if x]


def _names(text: str) -> List[str]:
    return [x for x in text.replace(" ", "").split(",") if x]


def _ask_offer(read: Read, write: Write, open_to: Sequence[str]) -> Optional[str]:
    write("A trade offer. Open now: " + ", ".join(open_to) + " -- empty answer = nothing.")
    try:
        to = int(read("  to player: "))
        give = (int(read("  gold you give: ") or 0), _numbers(read("  districts you give (numbers, commas): ")),
                _names(read("  cards you give: ")))
        ask = (int(read("  gold you ask: ") or 0), _numbers(read("  districts you ask: ")), _names(read("  cards you ask: ")))
    except ValueError:
        return None
    return build_offer(to, *give, *ask)


def _show_events(events: Sequence[Dict[str, object]], write: Write) -> None:
    for e in events:
        if e["kind"] == "said":
            write(f"  [round {e['round']}] player {e['player']} says: {e['data'].get('text')}")
        else:
            details = ", ".join(f"{k}={v}" for k, v in e["data"].items())
            write(f"  [round {e['round']}] player {e['player']}: {e['kind']}" + (f" ({details})" if details else ""))


def _choose(session, token: str, read: Read, write: Write) -> Optional[Tuple[str, Optional[str]]]:
    """One answer from the human: an action and its message, or None to leave."""
    view = seen(session, token)["view"]
    legal, offers = view["legal_actions"], [n for n in view["negotiations"] if n.startswith("offer:")]
    write("")
    write("Your choices:" + "".join(f"\n  {i}. {a}" for i, a in enumerate(legal, 1))
          + ("\n  o. make a trade offer" if offers else "") + "\n  q. leave the game")
    for _ in range(MAX_ANSWERS):
        answer = read("> ").strip()
        if answer.lower() == "q":
            return None
        if answer.lower() == "o" and offers:
            offer = _ask_offer(read, write, offers)
            if offer:
                return offer, None
        choice = parse_choice(answer, legal)
        if choice:
            return choice
        write("not a choice -- type the number of an action (and an optional message), o or q")
    raise RuntimeError("too many answers")


def play_console(opponents: Sequence[str], seed: int = 1, rounds: Optional[int] = None,
                 read: Read = input, write: Write = print) -> Dict[str, object]:
    """You (seat 0) against `opponents` (computer names). Returns whether the game is over, whether you left, and the
    ranking if it is over."""
    seats = (REMOTE,) + tuple(opponents)
    session = new_session(seats, seed=seed, rounds=rounds)
    token, since = next(iter(session.tokens)), 0
    while True:
        events = events_for(session, token, since)
        _show_events(events, write)
        since += len(events)
        if session.state.over:
            break
        write("")
        write(seen(session, token)["text"].split("\n## Your choices")[0])
        choice = _choose(session, token, read, write)
        if choice is None:
            write("You left the game.")
            return {"over": False, "left": True}
        try:
            act(session, token, choice[0], choice[1])
        except IllegalAction as error:
            write(f"refused by the engine: {error}")
    final = [{"seat": p, "player": "you" if p == 0 else seats[p], "net_worth": v} for p, v in ranking(session.state)]
    write("")
    write("Final ranking:" + "".join(f"\n  {i}. {r['player']} (seat {r['seat']}): {r['net_worth']} gold"
                                      for i, r in enumerate(final, 1)))
    return {"over": True, "left": False, "ranking": final}
