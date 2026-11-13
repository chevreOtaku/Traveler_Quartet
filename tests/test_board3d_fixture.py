"""The 3D study replays an actual engine action through public transport data."""
import json
import runpy
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parents[1] / "examples" / "board3d"


def test_fixture_is_exactly_reproducible_from_computer_play():
    actual = json.loads((DEMO / "fixture.json").read_text(encoding="utf-8"))
    expected = runpy.run_path(str(DEMO / "make_fixture.py"))["make_fixture"]()
    assert actual == json.loads(json.dumps(expected))
    move = next(e for e in actual["events"] if e["kind"] == "moved")
    seat, data = move["player"], move["data"]
    assert data["travel"] == "walk" and 2 <= data["steps"] <= 8
    assert actual["before"]["view"]["players"][seat]["position"] == data["from"]
    assert actual["after"]["view"]["players"][seat]["position"] == data["to"]
    assert actual["after"]["revision"] == actual["before"]["revision"] + 1
    assert all(e["index"] < actual["after"]["log_length"] for e in actual["events"])


def test_fixture_contains_only_public_snapshots_and_events():
    fixture = runpy.run_path(str(DEMO / "make_fixture.py"))["make_fixture"]()
    assert set(fixture) == {"before", "after", "events"}
    for snapshot in (fixture["before"], fixture["after"]):
        assert set(snapshot) == {"view", "over", "revision", "log_length", "seats"}
        assert set(snapshot["seats"]) <= {"human", "remote", "computer"}
        assert not {"me", "others", "seed", "decks", "tokens", "legal_actions", "negotiations"} & snapshot["view"].keys()
        assert all("cards" not in player for player in snapshot["view"]["players"])


def test_server_exposes_only_explicit_assets_on_loopback():
    server = runpy.run_path(str(DEMO / "serve.py"))["preview_server"](0)
    assert server.server_address[0] == "127.0.0.1"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    root = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        for name in ("", "app.js", "movement.js", "layout.js", "client.js", "camera.js", "play.js", "pawn.js", "scene.js",
                     "style.css", "vendor/three/three.module.js", "art/gallery.html", "art/merchants.js"):
            with urllib.request.urlopen(root + "/" + name) as reply:
                assert reply.status == 200 and reply.read()
        for name in ("../AGENTS.md", "make_fixture.py", "vendor/three/README.md"):
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(root + "/" + name)
            assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_preview_delegates_four_computers_and_bounded_public_events_to_real_server():
    server = runpy.run_path(str(DEMO / "serve.py"))["preview_server"](0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    root = f"http://127.0.0.1:{server.server_address[1]}"
    body = json.dumps({"seats": ["normal"] * 4, "seed": 1, "rounds": 1}).encode()
    try:
        request = urllib.request.Request(root + "/games", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as reply:
            created = json.load(reply)
        assert created["tokens"] == {}
        public = root + "/games/" + created["game"] + "/public"
        with urllib.request.urlopen(public) as reply:
            snapshot = json.load(reply)
        assert snapshot["over"] and snapshot["revision"] > 0
        assert len(snapshot["view"]["board"]) == 40
        assert len(snapshot["view"]["players"]) == 4
        end = snapshot["log_length"]
        with urllib.request.urlopen(public + f"/events?since=0&until={end}") as reply:
            rows = json.load(reply)["events"]
        assert [row["index"] for row in rows] == list(range(end))
        assert all(0 < row["revision"] <= snapshot["revision"] for row in rows)
        assert any(row["kind"] == "moved" and row["data"]["travel"] == "walk" for row in rows)
        with urllib.request.urlopen(public + "/events?since=0&until=1") as reply:
            assert json.load(reply)["events"] == rows[:1]
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(root + "/games/" + created["game"] + "/view")
        assert error.value.code == 401
    finally:
        server.shutdown()
        server.server_close()
