"""What happened since a player's last DECISION, in sentences (plan step 7) -- pure.

The PUBLIC events only, filtered exactly as the server's log is (`public_event`, shared with `match/session.py`): when a
rival draws a card he may KEEP, the player reads "a kept card", not which. Capped: beyond the cap, the summary says how
many earlier events it leaves out -- a forced forgetting, counted rather than hidden.
"""

from typing import Callable, Dict, List, Mapping, Sequence, Tuple

from traveler_quartet.rules.state import Event

KEPT_EFFECTS = ("keep", "curse")
SEALED_BID = "bid:"
SUMMARY_CAP = 30
TimedEvent = Tuple[int, Event]


def kept_cards(catalog: Mapping[str, Mapping[str, object]]) -> frozenset:
    return frozenset(cid for cid, card in catalog.items() if card.get("effect") in KEPT_EFFECTS)


def public_event(catalog: Mapping[str, Mapping[str, object]], event: Event, viewer) -> Dict[str, object]:
    """The event as `viewer` may see it (a seat, or None for a spectator). Two secrets are redacted for everyone but
    their author: which card a rival KEEPS, and the amount of a SEALED bid -- a message is recorded with the exact action
    it came with (`bid:55`), so the amount is cut from it (found by Codex in review); what the player SAID stays."""
    data = dict(event.data)
    if event.player == viewer:
        return {"kind": event.kind, "player": event.player, "data": data}
    if event.kind == "card" and data.get("card") in kept_cards(catalog):
        data = {"card": "a kept card"}
    if event.kind == "said" and str(data.get("action", "")).startswith(SEALED_BID):
        data["action"] = SEALED_BID.rstrip(":")
    return {"kind": event.kind, "player": event.player, "data": data}


def _square(names: Sequence[str], index) -> str:
    return f"[{index}] {names[index]}" if isinstance(index, int) and 0 <= index < len(names) else str(index)


def _sentences(names: Sequence[str], who: Callable) -> Dict[str, Callable[[Dict], str]]:
    return {
        "rolled": lambda d: f"rolled {d['dice'][0]} and {d['dice'][1]}",
        "bought": lambda d: f"bought {_square(names, d['square'])} for {d['price']}",
        "declined": lambda d: f"passed on {_square(names, d['square'])} (it goes to auction)",
        "bid": lambda d: f"bid {d['price']} on {_square(names, d['square'])}",
        "dropped": lambda d: f"dropped out of the auction on {_square(names, d['square'])}",
        "auction_won": lambda d: f"won the auction on {_square(names, d['square'])} for {d['price']}",
        "sealed_won": lambda d: f"won {_square(names, d['square'])} by sealed bid for {d['price']}",
        "rent_paid": lambda d: f"paid {d['amount']} rent to {who(d['to'])}",
        "passed_start": lambda d: f"passed Start (+{d['amount']})",
        "tax_paid": lambda d: f"paid {d['amount']} tax",
        "card": lambda d: f"drew {d['card'] if d['card'] == 'a kept card' else 'the card ' + str(d['card'])}",
        "offered": lambda d: f"made an offer to {who(d['to'])}",
        "countered": lambda d: f"made a counter-offer to {who(d['to'])}",
        "trade_done": lambda d: f"accepted the offer of {who(d['with'])}",
        "trade_refused": lambda d: f"refused the offer of {who(d['from'])}",
        "said": lambda d: f"said: \"{d.get('text')}\"",
        "built": lambda d: f"built on {_square(names, d['square'])} (level {d['level']})",
        "mortgaged": lambda d: f"mortgaged {_square(names, d['square'])}",
        "jumped": lambda d: f"jumped from {_square(names, d['from'])} to {_square(names, d['to'])}",
        "sent_to_dungeon": lambda d: "was sent to the dungeon",
        "paid_to_player": lambda d: f"paid {d['amount']} to {who(d['to'])}",
        "paid_by_bank": lambda d: f"received {d['amount']} from the bank",
        "paid_to_bank": lambda d: f"paid {d['amount']} to the bank",
        "jackpot_won": lambda d: f"won the jackpot ({d['amount']})",
        "bankrupt": lambda d: f"went bankrupt (to {who(d['to']) if isinstance(d['to'], int) else d['to']})",
    }


def sentence(event: Dict[str, object], names: Sequence[str], viewer: int) -> str:
    who = lambda seat: "you" if seat == viewer else f"player {seat}"
    data = {k: v for k, v in dict(event["data"]).items() if k != "bank"}
    subject = who(event["player"])
    readable = _sentences(names, who).get(str(event["kind"]))
    try:
        text = readable(data) if readable else None
    except (KeyError, IndexError, TypeError):
        text = None
    if text is None:
        details = ", ".join(f"{k}={v}" for k, v in data.items())
        text = f"{event['kind']}" + (f" ({details})" if details else "")
    if event["kind"] == "trade_refused" and data.get("from") == viewer:
        text = "refused your offer"
    return f"{subject} {text}"


def summary_lines(events: Sequence[TimedEvent], catalog: Mapping[str, Mapping[str, object]], names: Sequence[str],
                  viewer: int, cap: int = SUMMARY_CAP) -> List[str]:
    """One line per public event (round, sentence); the oldest beyond `cap` are counted, not shown."""
    shown = list(events)[-cap:] if cap else []
    left_out = len(events) - len(shown)
    lines = [f"- ({left_out} earlier events not shown)"] if left_out else []
    return lines + [f"- round {r}: {sentence(public_event(catalog, e, viewer), names, viewer)}" for r, e in shown]
