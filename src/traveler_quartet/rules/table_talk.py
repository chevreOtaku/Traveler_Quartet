"""Table talk -- an option, off by default (`talks_per_turn` in the economy): at the start of its turn a player may
SPEAK to one rival, who must ANSWER before the turn goes on. The words travel as the players' table messages; the
engine only gives the floor and takes it back."""

from dataclasses import replace
from typing import Tuple

from traveler_quartet.rules.state import Event, GameState, Step


def talk_actions(state: GameState) -> Tuple[str, ...]:
    """`talk:<player>` for each active rival, while the turn has talks left."""
    if state.talks >= state.economy.talks_per_turn:
        return ()
    return tuple(f"talk:{p}" for p in range(len(state.players)) if p != state.current and not state.players[p].out)


def talk(state: GameState, listener: int) -> Step:
    state = replace(state, pending="talk", listener=listener, talks=state.talks + 1)
    return state, (Event("talked", state.current, (("to", listener),)),)


def reply(state: GameState) -> Step:
    """The answer gives the floor back to the player whose turn it is."""
    listener = state.listener
    return replace(state, pending="roll", listener=None), (Event("replied", listener, (("to", state.current),)),)
