"""The connected board delegates gameplay and serves only its explicit local assets."""
import json
import runpy
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "examples" / "board"

@pytest.fixture
def preview():
    server = runpy.run_path(str(PREVIEW / "serve.py"))["preview_server"](port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    root = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield root
    finally:
        server.shutdown()
        server.server_close()

def request(root, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    raw = None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(root + path, data=raw, headers=headers)) as reply:
        return json.load(reply)

def test_preview_serves_assets_but_not_arbitrary_repository_files(preview):
    for name in ("", "board.css", "model.js", "client.js", "render.js", "app.js", "merchant.svg", "village.svg"):
        with urllib.request.urlopen(preview + "/" + name) as reply:
            assert reply.status == 200 and reply.read()
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(preview + "/../AGENTS.md")
    assert error.value.code == 404

def test_connected_preview_plays_through_the_existing_http_contract(preview):
    created = request(preview, "/games", {"seats": ["remote", "normal"], "seed": 1, "rounds": 1})
    game_id, token = created["game"], next(iter(created["tokens"]))
    path = f"/games/{game_id}"
    seen = request(preview, path + "/view", token=token)
    assert len(seen["view"]["board"]) == 40
    for _ in range(100):
        if seen["over"]:
            break
        action = seen["view"]["legal_actions"][0]
        seen = request(preview, path + "/act", {"action": action, "message": ""}, token)
    assert seen["over"] and len(seen["view"]["ranking"]) == 2
    public = request(preview, path + "/public")
    assert "players" in public["view"] and "me" not in public["view"]
    assert "legal_actions" not in public["view"]
    assert all("cards" not in p for p in public["view"]["players"])

def test_front_uses_text_nodes_and_has_no_external_asset_dependencies():
    for name in ("render.js", "app.js", "client.js"):
        source = (PREVIEW / name).read_text(encoding="utf-8")
        assert "innerHTML" not in source and "insertAdjacentHTML" not in source
    html = (PREVIEW / "index.html").read_text(encoding="utf-8")
    assert "https://" not in html and "http://" not in html
