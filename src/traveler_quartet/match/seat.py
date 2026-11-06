"""Playing ONE seat of the local server (step 7a) from a terminal, one command per move -- for a person or an agent who
wants to see exactly what a player sees, without a browser. Start the server first (`traveler-quartet serve`), then:

    python -m traveler_quartet.match.seat new remote,normal,normal,normal 7   start a game, you are the remote seat
    python -m traveler_quartet.match.seat view                                 your state text
    python -m traveler_quartet.match.seat act roll good luck                   play an action (+ an optional message)
    python -m traveler_quartet.match.seat events 12                            the log, from event 12 on

The game id and your token are kept in a small file (`--store`, in the system temp folder by default), never in a
command line or a URL. The standard library only, like the server.
"""

import argparse
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_BASE = "http://127.0.0.1:8765"
DEFAULT_STORE = Path(tempfile.gettempdir()) / "traveler-quartet-seat.json"
Reply = Tuple[int, Dict[str, object]]


def request(base: str, method: str, path: str, body: Optional[dict] = None, token: Optional[str] = None) -> Reply:
    """One call to the server; an HTTP error is a reply too (its status and its JSON)."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m traveler_quartet.match.seat")
    parser.add_argument("--base", default=None, help=f"the server (default {DEFAULT_BASE}, or the one of `new`)")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE, help="where the game id and the token are kept")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new")
    new.add_argument("seats", help="comma-separated, e.g. remote,normal,hard")
    new.add_argument("seed", type=int)
    commands.add_parser("view")
    act = commands.add_parser("act")
    act.add_argument("action")
    act.add_argument("message", nargs="*")
    events = commands.add_parser("events")
    events.add_argument("since", type=int, nargs="?", default=0)
    return parser


def _shown(status: int, data: Dict[str, object]) -> Tuple[int, str]:
    if 200 <= status < 300:
        return 0, str(data.get("text") or json.dumps(data, indent=1, ensure_ascii=False))
    legal = data.get("legal_actions")
    return 1, f"{status}: {data.get('error')}" + (f"\nlegal now: {', '.join(legal)}" if legal else "")


def _new(base: str, store: Path, seats: str, seed: int) -> Tuple[int, str]:
    status, data = request(base, "POST", "/games", {"seats": seats.split(","), "seed": seed})
    if status != 201:
        return _shown(status, data)
    store.write_text(json.dumps({"base": base, "game": data["game"], "token": next(iter(data["tokens"]))}))
    status, data = request(base, "GET", f"/games/{data['game']}/view", token=next(iter(data["tokens"])))
    return _shown(status, data)


def _played(args: argparse.Namespace, saved: Dict[str, str], base: str) -> Tuple[int, str]:
    game, token = saved["game"], saved["token"]
    if args.command == "view":
        return _shown(*request(base, "GET", f"/games/{game}/view", token=token))
    if args.command == "act":
        body = {"action": args.action, "message": " ".join(args.message) or None}
        return _shown(*request(base, "POST", f"/games/{game}/act", body, token))
    status, data = request(base, "GET", f"/games/{game}/events?since={args.since}", token=token)
    return (0, json.dumps(data["events"], indent=1, ensure_ascii=False)) if status == 200 else _shown(status, data)


def run(argv: List[str]) -> Tuple[int, str]:
    """The whole command: its exit code (0 done, 1 refused by the server, 2 no game yet) and what it prints."""
    args = _parser().parse_args(argv)
    if args.command == "new":
        return _new(args.base or DEFAULT_BASE, args.store, args.seats, args.seed)
    if not args.store.exists():
        return 2, f"no game yet in {args.store}: start one with `new`"
    saved = json.loads(args.store.read_text())
    return _played(args, saved, args.base or saved["base"])


def main() -> int:
    code, out = run(sys.argv[1:])
    print(out)
    return code


if __name__ == "__main__":
    sys.exit(main())
