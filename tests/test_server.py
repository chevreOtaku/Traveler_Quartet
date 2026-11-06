"""The local server (step 7a): the standard library only, the page ASKS (no WebSocket), designed as if the players were
far. `handle` is the whole server without the network; one test runs the real HTTP server on a free port."""

import json
import threading
import urllib.error
import urllib.request

from traveler_quartet.match.server import Registry, handle, make_server


def _create(reg, seats=("remote", "normal"), seed=1):
    status, body = handle(reg, "POST", "/games", {}, json.dumps({"seats": list(seats), "seed": seed}).encode())
    return status, body


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_creating_a_game_gives_one_token_per_remote_seat():
    status, body = _create(Registry())
    assert status == 201 and list(body["tokens"].values()) == [0] and body["game"]


def test_a_player_reads_his_view_with_his_token_only():
    reg = Registry()
    _, created = _create(reg)
    token = next(iter(created["tokens"]))
    status, body = handle(reg, "GET", f"/games/{created['game']}/view", _auth(token), b"")
    assert status == 200 and body["view"]["me"]["seat"] == 0
    assert handle(reg, "GET", f"/games/{created['game']}/view", _auth("wrong"), b"")[0] == 401
    assert handle(reg, "GET", f"/games/{created['game']}/view", {}, b"")[0] == 401


def test_an_action_is_played_and_a_bad_one_says_why():
    reg = Registry()
    _, created = _create(reg)
    game, token = created["game"], next(iter(created["tokens"]))
    bad = handle(reg, "POST", f"/games/{game}/act", _auth(token), json.dumps({"action": "fly"}).encode())
    assert bad[0] == 400 and "roll" in bad[1]["legal_actions"]
    good = handle(reg, "POST", f"/games/{game}/act", _auth(token), json.dumps({"action": "roll", "message": "go"}).encode())
    assert good[0] == 200 and "view" in good[1]


def test_acting_out_of_turn_is_a_conflict():
    reg = Registry()
    _, created = _create(reg, seats=("remote", "remote"))
    game = created["game"]
    waiting = next(t for t, seat in created["tokens"].items() if seat == 1)
    assert handle(reg, "POST", f"/games/{game}/act", _auth(waiting), json.dumps({"action": "roll"}).encode())[0] == 409


def test_the_log_is_read_from_an_index():
    reg = Registry()
    _, created = _create(reg)
    game, token = created["game"], next(iter(created["tokens"]))
    handle(reg, "POST", f"/games/{game}/act", _auth(token), json.dumps({"action": "roll"}).encode())
    everything = handle(reg, "GET", f"/games/{game}/events?since=0", _auth(token), b"")[1]["events"]
    later = handle(reg, "GET", f"/games/{game}/events?since=2", _auth(token), b"")[1]["events"]
    assert len(later) == len(everything) - 2


def test_unknown_games_paths_and_bad_requests():
    reg = Registry()
    assert handle(reg, "GET", "/games/nope/view", _auth("t"), b"")[0] == 404
    assert handle(reg, "GET", "/elsewhere", {}, b"")[0] == 404
    assert handle(reg, "POST", "/games", {}, b"not json")[0] == 400
    assert _create(reg, seats=("remote", "wizard"))[0] == 400


def test_the_real_server_answers_on_localhost():
    server = make_server(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/games"
        request = urllib.request.Request(url, data=json.dumps({"seats": ["remote", "normal"]}).encode(), method="POST")
        with urllib.request.urlopen(request) as answer:
            assert answer.status == 201 and json.loads(answer.read())["tokens"]
        try:
            urllib.request.urlopen(url.replace("/games", "/nowhere"))
        except urllib.error.HTTPError as error:
            assert error.code == 404
    finally:
        server.shutdown()
        server.server_close()
    assert server.server_address[0] == "127.0.0.1"


def test_the_command_knows_the_serve_mode_and_its_port():
    from traveler_quartet.__main__ import build_parser
    args = build_parser().parse_args(["serve", "--port", "9000"])
    assert args.mode == "serve" and args.port == 9000
