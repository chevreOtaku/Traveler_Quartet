from dataclasses import replace

from traveler_quartet.rules.state import GameState


def _active(state: GameState) -> int:
    return sum(1 for p in state.players if not p.out)


def end_turn(state: GameState) -> GameState:
    if _active(state) <= 1:
        return replace(state, pending="over", doubles=0)
    following, next_round = state.current, state.round
    while True:
        following = (following + 1) % len(state.players)
        next_round += following == 0
        if not state.players[following].out:
            break
    if next_round > state.economy.rounds:
        return replace(state, pending="over", doubles=0)
    return replace(state, current=following, round=next_round, pending="roll", doubles=0)


def finish(state: GameState) -> GameState:
    """After a move is fully resolved: a double outside the dungeon plays again, anything else ends the turn."""
    me = state.players[state.current]
    if state.doubles > 0 and me.dungeon_turns == 0 and not me.out:
        return replace(state, pending="roll")
    return end_turn(state)
