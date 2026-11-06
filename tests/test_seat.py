"""Playing ONE seat of the local server from a terminal, one command per move (`python -m traveler_quartet.match.seat`):
for a person or an agent who wants to test what a player sees. Every test runs the real HTTP server on a free port."""

import json
import threading

import pytest

from traveler_quartet.match.seat import run
from traveler_quartet.match.server import make_server


@pytest.fixture
def base():
    server = make_server(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _seat(base, store, *argv):
    return run(["--base", base, "--store", str(store), *argv])


def test_new_starts_a_game_and_shows_the_players_text(base, tmp_path):
    code, out = _seat(base, tmp_path / "seat.json", "new", "remote,normal", "1")
    assert code == 0 and "you are player 0" in out and "`roll`" in out


def test_the_game_and_the_token_are_kept_for_the_next_commands(base, tmp_path):
    store = tmp_path / "seat.json"
    _seat(base, store, "new", "remote,normal", "1")
    saved = json.loads(store.read_text())
    assert set(saved) == {"base", "game", "token"} and saved["base"] == base
    code, out = _seat(base, store, "view")
    assert code == 0 and "you are player 0" in out


def test_a_move_is_played_and_the_new_text_is_shown(base, tmp_path):
    store = tmp_path / "seat.json"
    _seat(base, store, "new", "remote,normal", "1")
    code, out = _seat(base, store, "act", "roll", "good", "luck")
    assert code == 0 and "you are player 0" in out and "## Your choices" in out
    code, out = _seat(base, store, "events")
    assert code == 0 and "good luck" in out and "rolled" in out


def test_an_illegal_move_fails_and_lists_the_legal_ones(base, tmp_path):
    store = tmp_path / "seat.json"
    _seat(base, store, "new", "remote,normal", "1")
    code, out = _seat(base, store, "act", "fly")
    assert code == 1 and "roll" in out.split("legal now:")[1]


def test_events_since_n_skips_the_first_n(base, tmp_path):
    store = tmp_path / "seat.json"
    _seat(base, store, "new", "remote,normal", "1")
    _seat(base, store, "act", "roll", "hello")
    _, all_events = _seat(base, store, "events")
    _, later = _seat(base, store, "events", "1")
    assert "hello" in all_events and "hello" not in later


def test_a_table_without_a_remote_seat_is_refused_before_it_is_created(base, tmp_path):
    store = tmp_path / "seat.json"
    code, out = _seat(base, store, "new", "normal,normal", "1")
    assert code == 2 and "remote" in out and not store.exists()


def test_a_command_before_new_says_so_instead_of_crashing(tmp_path):
    code, out = run(["--store", str(tmp_path / "none.json"), "view"])
    assert code == 2 and "new" in out


def test_the_text_never_shows_the_seed_or_the_decks(base, tmp_path):
    _, out = _seat(base, tmp_path / "seat.json", "new", "remote,normal", "1")
    assert "seed" not in out.lower() and "decks" not in out.lower()
