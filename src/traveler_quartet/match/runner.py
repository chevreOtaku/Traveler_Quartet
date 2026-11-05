from typing import Callable, List, Sequence, Tuple

from traveler_quartet.rules.engine import Event, GameState, apply, legal_actions

Chooser = Callable[[GameState, Tuple[str, ...]], str]
TimedEvent = Tuple[int, Event]


def play_game_rounds(state: GameState, choosers: Sequence[Chooser]) -> Tuple[GameState, Tuple[TimedEvent, ...]]:
    """Ask the player named by the pending question until the game is over; each event with its round."""
    if len(choosers) != len(state.players):
        raise ValueError(f"{len(state.players)} players need {len(state.players)} choosers, got {len(choosers)}")
    timed: List[TimedEvent] = []
    while not state.over:
        legal = legal_actions(state)
        round_now = state.round
        state, step_events = apply(state, choosers[state.current](state, legal))
        timed.extend((round_now, event) for event in step_events)
    return state, tuple(timed)


def play_game(state: GameState, choosers: Sequence[Chooser]) -> Tuple[GameState, Tuple[Event, ...]]:
    final, timed = play_game_rounds(state, choosers)
    return final, tuple(event for _, event in timed)
