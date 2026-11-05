from typing import Callable, List, Sequence, Tuple

from traveler_quartet.rules.engine import Event, GameState, apply, legal_actions

Chooser = Callable[[GameState, Tuple[str, ...]], str]


def play_game(state: GameState, choosers: Sequence[Chooser]) -> Tuple[GameState, Tuple[Event, ...]]:
    """Ask the player named by the pending question until the game is over."""
    if len(choosers) != len(state.players):
        raise ValueError(f"{len(state.players)} players need {len(state.players)} choosers, got {len(choosers)}")
    events: List[Event] = []
    while not state.over:
        legal = legal_actions(state)
        state, step_events = apply(state, choosers[state.current](state, legal))
        events.extend(step_events)
    return state, tuple(events)
