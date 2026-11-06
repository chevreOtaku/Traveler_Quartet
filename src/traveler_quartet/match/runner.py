from typing import Callable, List, Optional, Sequence, Tuple, Union

from traveler_quartet.rules.engine import Event, GameState, actor, apply, legal_actions

Chooser = Callable[[GameState, Tuple[str, ...]], Union[str, Tuple[str, str]]]
TimedEvent = Tuple[int, Event]
StepObserver = Callable[[GameState, Tuple[TimedEvent, ...]], None]
MAX_STEPS = 20000


def play_game_rounds(state: GameState, choosers: Sequence[Chooser],
                     max_steps: int = MAX_STEPS,
                     on_step: Optional[StepObserver] = None) -> Tuple[GameState, Tuple[TimedEvent, ...]]:
    """Ask the player named by the pending question until the game is over; each event with its round."""
    if len(choosers) != len(state.players):
        raise ValueError(f"{len(state.players)} players need {len(state.players)} choosers, got {len(choosers)}")
    timed: List[TimedEvent] = []
    steps = 0
    while not state.over:
        steps += 1
        if steps > max_steps:
            raise RuntimeError(f"the game did not end in {max_steps} steps (round {state.round}, pending {state.pending!r})")
        legal, who, round_now = legal_actions(state), actor(state), state.round
        event_start = len(timed)
        answer = choosers[who](state, legal)
        action, message = answer if isinstance(answer, tuple) else (answer, None)
        if message:
            timed.append((round_now, Event("said", who, (("action", action), ("text", message)))))
        state, step_events = apply(state, action)
        timed.extend((round_now, event) for event in step_events)
        if on_step is not None:
            on_step(state, tuple(timed[event_start:]))
    return state, tuple(timed)


def play_game(state: GameState, choosers: Sequence[Chooser]) -> Tuple[GameState, Tuple[Event, ...]]:
    final, timed = play_game_rounds(state, choosers)
    return final, tuple(event for _, event in timed)
