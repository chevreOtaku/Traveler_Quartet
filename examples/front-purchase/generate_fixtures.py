"""Regenerate the public purchase demo snapshots using the real rules engine."""
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from traveler_quartet.players.view import spectator
from traveler_quartet.rules.engine import apply, new_game
from traveler_quartet.rules.state import update_player

def snapshots():
    state = new_game(seed=1, player_count=4)
    for seat, position in enumerate((1, 8, 16, 31)):
        state = update_player(state, seat, position=position)
    owners = list(state.owners)
    owners[3] = 2
    state = replace(state, current=0, pending="buy", round=3, last_dice=(1, 1),
                    doubles=1, owners=tuple(owners))
    bought, _ = apply(state, "buy")
    passed, _ = apply(state, "pass")
    return {name: spectator(value) for name, value in (
        ("initial", state), ("buy", bought), ("pass", passed))}

if __name__ == "__main__":
    text = "globalThis.PURCHASE_FIXTURES = " + json.dumps(snapshots(), separators=(",", ":")) + ";\n"
    Path(__file__).with_name("fixtures.js").write_text(text, encoding="utf-8")
