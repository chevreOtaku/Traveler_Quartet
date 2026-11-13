import json
import random
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Tuple

from traveler_quartet.rules.board import DATA_DIR
from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.state import GameState, update_player

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


def keep_card(state: GameState, player: int, card_id: str) -> GameState:
    """A kept card goes to the hand and LEAVES its deck while it is held: it cannot be drawn twice."""
    deck = deck_of(state, card_id)
    state = update_player(state, player, cards=state.players[player].cards + (card_id,))
    return replace(state, decks=tuple((d, tuple(c for c in ids if c != card_id)) if d == deck else (d, ids)
                                      for d, ids in state.decks))


def return_card(state: GameState, player: int, card_id: str) -> GameState:
    """A held card that is played, or whose holder goes out, leaves the hand and goes back UNDER its deck."""
    held = list(state.players[player].cards)
    held.remove(card_id)
    deck = deck_of(state, card_id)
    state = update_player(state, player, cards=tuple(held))
    return replace(state, decks=tuple((d, ids + (card_id,)) if d == deck else (d, ids) for d, ids in state.decks))


def card_die(state: GameState) -> Tuple[GameState, int]:
    """One die for a card, taken from the game's roll sequence (so a game still replays)."""
    face = roll(state.seed, state.rolls)[0]
    return replace(state, rolls=state.rolls + 1), face


def carousel(state: GameState) -> str:
    """The town picked by the carousel, reproducibly."""
    towns = sorted(state.board.towns)
    return random.Random(f"carousel:{state.seed}:{state.rolls}").choice(towns)
