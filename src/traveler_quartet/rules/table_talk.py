"""Table talk -- an option, off by default (`talks_per_turn` in the economy): at ANY decision a player may first SPEAK
to a rival, who must ANSWER; then the same question is asked again. Each seat has its own talks in a turn. The words
travel as the players' table messages; the engine only gives the floor and takes it back."""

from dataclasses import replace
from typing import Tuple

from traveler_quartet.rules.state import Event, GameState, Step


def spent(state: GameState, seat: int) -> int:
    return state.talks[seat] if seat < len(state.talks) else 0


def talk_actions(state: GameState, me: int) -> Tuple[str, ...]:
    """`talk:<player>` for each active rival of `me`, the seat that must answer the pending question."""
    if state.pending in ("talk", "over") or spent(state, me) >= state.economy.talks_per_turn:
        return ()
    return tuple(f"talk:{p}" for p in range(len(state.players)) if p != me and not state.players[p].out)


def talk(state: GameState, me: int, listener: int) -> Step:
    counts = [spent(state, seat) for seat in range(len(state.players))]
    counts[me] += 1
    state = replace(state, pending="talk", listener=listener, speaker=me, resume=state.pending, talks=tuple(counts))
    return state, (Event("talked", me, (("to", listener),)),)


def reply(state: GameState) -> Step:
    """The answer gives the floor back: the question that was pending is asked again."""
    listener, speaker = state.listener, state.speaker
    state = replace(state, pending=state.resume, listener=None, speaker=None, resume=None)
    return state, (Event("replied", listener, (("to", speaker),)),)
