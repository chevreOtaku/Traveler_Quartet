import argparse
import sys
from typing import List, Optional

from traveler_quartet import __version__

MODES = ("play", "cli", "tournament")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="traveler-quartet")
    parser.add_argument("--version", action="version", version=f"traveler-quartet {__version__}")
    parser.add_argument("mode", choices=MODES, nargs="?")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode is None:
        parser.print_help()
        return 0
    print(f"traveler-quartet: '{args.mode}' is not built yet.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
