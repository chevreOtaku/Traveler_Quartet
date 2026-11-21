"""The view a HUMAN in a real debt receives (`GET /games/<id>/view` gives `view(state, seat)`), written as JSON for the
3D page's tests (`board3d-debt-view.json`): the page is tested on what the engine really sends, not on a hand-made
view. Run `python tests/debt_view.py` to write it again; `test_trade_in_debt.py` checks it is up to date."""

import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from factory import at, build_levels, cash, game, own  # noqa: E402
from traveler_quartet.players.view import view  # noqa: E402
from traveler_quartet.rules.dice import roll  # noqa: E402
from traveler_quartet.rules.engine import apply  # noqa: E402

TARGET = Path(__file__).with_name("board3d-debt-view.json")


def debt_view() -> dict:
    """Seat 0 lands on the creditor's built dark blue (rent 680) with 300 gold and the purple town (11, 13, 14)."""
    state = build_levels(own(game(players=3), 1, 37, 39), {37: 4, 39: 4})
    state = cash(at(own(state, 0, 11, 13, 14), 0, (37 - sum(roll(state.seed, 0))) % 40), 0, 300)
    state, _ = apply(state, "roll")
    assert state.pending == "debt"
    return json.loads(json.dumps({"view": view(state, 0), "revision": 1, "over": False}))


if __name__ == "__main__":
    TARGET.write_text(json.dumps(debt_view(), indent=1) + "\n", encoding="utf-8")
