"""The local server (step 7a) -- the standard library only; the page ASKS (no WebSocket); designed as if the players were
FAR: a game, one token per remote player, every answer checked by the engine.

    POST /games                      {"seats": ["remote", "normal", ...], "seed": 1}  -> 201 {"game", "tokens"}
    GET  /games/<id>/view            -> 200 {"view", "text", "over", "log_length"}
    POST /games/<id>/act             {"action": "...", "message": "..."}      -> 200 {"view", ...}
    GET  /games/<id>/events?since=n  -> 200 {"events": [...]}
    GET  /games/<id>/public          -> 200 {"view", "over", "log_length"}  -- a SPECTATOR (the stream), no token
    GET  /games/<id>/public/events?since=n -> 200 {"events": [...]}       -- every kept card stays "a kept card"

`POST /games` may give "rounds" (a shorter game to try things; a positive integer).

The token goes in the `Authorization: Bearer <token>` header, never in the URL (it would end up in logs). 401: unknown
token ; 409: not your turn ; 400: a bad request or an illegal action (with the legal ones) ; 404: no such game or path.
`handle` is the whole server without the network; `make_server` binds it to 127.0.0.1 by default.
"""

import json
import secrets
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Dict, Mapping, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from traveler_quartet.match.session import (NotYourTurn, Session, StaleRevision, Unauthorized, act, events_for,
                                            new_session, public_events, seen, watched)
from traveler_quartet.rules.engine import IllegalAction, legal_actions

Reply = Tuple[int, Dict[str, object]]


@dataclass
class Registry:
    games: Dict[str, Session] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _token(headers: Mapping[str, str]) -> str:
    value = next((v for k, v in headers.items() if k.lower() == "authorization"), "")
    return value[len("Bearer "):] if value.startswith("Bearer ") else ""


def _json(body: bytes) -> Dict[str, object]:
    data = json.loads(body.decode("utf-8") or "{}")
    if not isinstance(data, dict):
        raise ValueError("the body must be a JSON object")
    return data


def _rounds(data: Mapping[str, object]):
    rounds = data.get("rounds")
    if rounds is None:
        return None
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
        raise ValueError("rounds must be a positive integer")
    return rounds


def _create(reg: Registry, body: bytes) -> Reply:
    data = _json(body)
    session = new_session(tuple(data.get("seats", ())), seed=int(data.get("seed", 1)), rounds=_rounds(data))
    game = secrets.token_hex(4)
    reg.games[game] = session
    return 201, {"game": game, "tokens": session.tokens}


def _window(query: str) -> Tuple[int, Optional[int]]:
    """`since` (included) and `until` (EXCLUDED, optional) of an events read."""
    params = parse_qs(query)
    until = params.get("until", [None])[0]
    return int(params.get("since", ["0"])[0]), (None if until is None else int(until))


def _expected_revision(data: Mapping[str, object]) -> Optional[int]:
    value = data.get("expected_revision")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("expected_revision must be a non-negative integer")
    return value


def _on_game(reg: Registry, game: str, verb: str, headers: Mapping[str, str], body: bytes, query: str) -> Reply:
    session, token = reg.games[game], _token(headers)
    if verb == "view":
        return 200, seen(session, token)
    if verb == "events":
        return 200, {"events": events_for(session, token, *_window(query))}
    data = _json(body)
    try:
        act(session, token, str(data.get("action", "")), data.get("message"), _expected_revision(data))
    except IllegalAction as error:
        return 400, {"error": str(error), "legal_actions": list(legal_actions(session.state))}
    return 200, seen(session, token)


def _spectate(reg: Registry, parts, query: str) -> Reply:
    if parts[1] not in reg.games:
        return 404, {"error": "no such game"}
    session = reg.games[parts[1]]
    if len(parts) == 3:
        return 200, watched(session)
    if parts[3] != "events":
        return 404, {"error": "no such path"}
    return 200, {"events": public_events(session, *_window(query))}


def handle(reg: Registry, method: str, path: str, headers: Mapping[str, str], body: bytes) -> Reply:
    url = urlparse(path)
    parts = [p for p in url.path.split("/") if p]
    try:
        with reg.lock:
            if method == "POST" and parts == ["games"]:
                return _create(reg, body)
            if method == "GET" and len(parts) in (3, 4) and parts[0] == "games" and parts[2] == "public":
                return _spectate(reg, parts, url.query)
            if len(parts) == 3 and parts[0] == "games" and (method, parts[2]) in (("GET", "view"), ("GET", "events"),
                                                                                  ("POST", "act")):
                if parts[1] not in reg.games:
                    return 404, {"error": "no such game"}
                return _on_game(reg, parts[1], parts[2], headers, body, url.query)
    except Unauthorized as error:
        return 401, {"error": str(error)}
    except (NotYourTurn, StaleRevision) as error:
        return 409, {"error": str(error)}
    except ValueError as error:
        return 400, {"error": str(error)}
    return 404, {"error": "no such path"}


def _handler(reg: Registry):
    class Handler(BaseHTTPRequestHandler):
        def _answer(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            status, payload = handle(reg, method, self.path, dict(self.headers), self.rfile.read(length))
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path == "/":
                raw = files("traveler_quartet").joinpath("web/index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            self._answer("GET")

        def do_POST(self) -> None:
            self._answer("POST")

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _handler(Registry()))
