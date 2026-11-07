"""The per-rival NOTEBOOK of an AI player (plan step 8) -- pure.

Private notes, one per rival, that the player rewrites when it wants; an empty note forgets. Each note is capped: the cap
forces the choice, and what it cuts is counted as forced forgetting. Notes are only ever kept for RIVALS (never itself,
never a seat that does not exist). Nothing here is shown to another player: the notebook lives in the player, not the view.
"""

from typing import Dict, Mapping, Tuple

NOTES_FORMAT = (' You may also add "notes": {"<player number>": "<your private note on that rival>"} -- notes are '
                'yours alone and kept between your decisions; give a note again to change it, an empty note forgets it.')


def update_notes(notes: Mapping[str, str], proposed, me: int, players: int, cap: int) -> Tuple[Dict[str, str], int]:
    """The notebook after a reply, and how many characters the cap cut."""
    kept, cut = dict(notes), 0
    if not isinstance(proposed, dict):
        return kept, 0
    rivals = {str(seat) for seat in range(players) if seat != me}
    for key, text in proposed.items():
        key = str(key)
        if key not in rivals or not isinstance(text, str):
            continue
        text = text.strip()
        if not text:
            kept.pop(key, None)
            continue
        cut += max(0, len(text) - cap)
        kept[key] = text[:cap]
    return kept, cut


def notes_section(notes: Mapping[str, str], cap: int) -> str:
    lines = [f"- player {seat}: {text}" for seat, text in sorted(notes.items())] or ["- none yet"]
    return (f"\n\n## Your private notes on the other players (yours alone; at most {cap} characters each)\n"
            + "\n".join(lines))
