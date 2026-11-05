import json
import random
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Tuple

from traveler_quartet.rules.board import DATA_DIR
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.state import GameState

DECKS = ("chance", "event", "adventurer")
Card = Mapping[str, object]


def load_cards(path: Path = DATA_DIR / "cards.json") -> Mapping[str, Card]:
    cards = json.loads(path.read_text(encoding="utf-8"))["cards"]
    return MappingProxyType({c["id"]: MappingProxyType(dict(c)) for c in cards})


def shuffled_decks(catalog: Mapping[str, Card], seed: int) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """Every deck shuffled from the game's seed: the same seed, the same decks."""
    out = []
    for deck in DECKS:
        ids = [cid for cid, card in catalog.items() if card["deck"] == deck]
        random.Random(f"deck:{deck}:{seed}").shuffle(ids)
        out.append((deck, tuple(ids)))
    return tuple(out)


def deck_of(state: GameState, card_id: str) -> str:
    return state.catalog[card_id]["deck"]


def draw(state: GameState, deck: str) -> Tuple[GameState, Card]:
    """The top card; it goes back under its deck."""
    decks = dict(state.decks)
    top, rest = decks[deck][0], decks[deck][1:]
    decks[deck] = rest + (top,)
    return replace(state, decks=tuple((d, decks[d]) for d, _ in state.decks)), state.catalog[top]


def card_die(state: GameState) -> Tuple[GameState, int]:
    """One die for a card, taken from the game's roll sequence (so a game still replays)."""
    face = roll(state.seed, state.rolls)[0]
    return replace(state, rolls=state.rolls + 1), face


def carousel(state: GameState) -> str:
    """The town picked by the carousel, reproducibly."""
    towns = sorted(state.board.towns)
    return random.Random(f"carousel:{state.seed}:{state.rolls}").choice(towns)
