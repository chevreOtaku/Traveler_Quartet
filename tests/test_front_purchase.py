"""The purchase study must stay an offline presentation of real public engine snapshots."""
import json
import re
import runpy
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "examples" / "front-purchase"

def test_purchase_demo_snapshots_match_the_engine():
    actual = json.loads((DEMO / "fixtures.js").read_text(encoding="utf-8").removeprefix(
        "globalThis.PURCHASE_FIXTURES = ").removesuffix(";\n"))
    expected = runpy.run_path(str(DEMO / "generate_fixtures.py"))["snapshots"]()
    assert actual == json.loads(json.dumps(expected))

def test_purchase_demo_never_ships_private_fields():
    actual = json.loads((DEMO / "fixtures.js").read_text(encoding="utf-8").split(" = ", 1)[1][:-2])
    for state in actual.values():
        assert not {"me", "others", "seed", "decks", "tokens", "legal_actions", "negotiations"} & state.keys()
        assert all("cards" not in player for player in state["players"])

def test_purchase_demo_assets_are_local_and_small():
    html = (DEMO / "index.html").read_text(encoding="utf-8")
    assets = re.findall(r'(?:src|href)="([^"]+)"', html)
    for asset in assets:
        assert not re.match(r"(?:https?:)?//", asset)
        if asset not in ("./", "data:,"):
            assert (DEMO / asset).is_file()
    assert sum(p.stat().st_size for p in DEMO.iterdir() if p.is_file()) < 5_000_000
