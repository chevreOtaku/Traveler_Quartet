import argparse
import json
import sys
from typing import List, Optional

from traveler_quartet import __version__

MODES = ("play", "cli", "tournament")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="traveler-quartet")
    parser.add_argument("--version", action="version", version=f"traveler-quartet {__version__}")
    parser.add_argument("mode", choices=MODES, nargs="?")
    parser.add_argument("--games", type=int, default=1000, help="tournament: number of games")
    parser.add_argument("--seed", type=int, default=1, help="tournament: seed of the first game")
    parser.add_argument("--seats", default="normal,normal,normal,normal",
                        help="tournament: the computers at the table, comma-separated (easy, normal, hard, adaptive)")
    parser.add_argument("--no-disasters", action="store_true", help="tournament: remove the disaster cards")
    parser.add_argument("--rounds", type=int, default=None, help="tournament: simulate another game length")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=AMOUNT",
                        help="tournament: simulate another amount, by its name in economy.json (repeatable)")
    return parser


def _changes(pairs: List[str]) -> dict:
    return {name: int(amount) for name, _, amount in (pair.partition("=") for pair in pairs)}


def _tournament(args: argparse.Namespace) -> int:
    from traveler_quartet.match.tournament import run_tournament
    report = run_tournament(games=args.games, first_seed=args.seed, seats=args.seats.split(","),
                            disasters=not args.no_disasters, rounds=args.rounds,
                            changes=_changes(args.set))
    print(json.dumps({k: v for k, v in report.items() if k != "winners"}, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode is None:
        parser.print_help()
        return 0
    if args.mode == "tournament":
        return _tournament(args)
    print(f"traveler-quartet: '{args.mode}' is not built yet.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
