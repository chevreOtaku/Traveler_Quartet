from dataclasses import replace

from traveler_quartet.rules.state import Event, GameState, Step, change_cash, update_player
from traveler_quartet.rules.turns import end_turn


def dungeon_square(state: GameState) -> int:
    return next(i for i, s in enumerate(state.board.squares) if s.kind == "dungeon")


def in_dungeon(state: GameState) -> bool:
    return state.players[state.current].dungeon_turns > 0


def can_pay_exit(state: GameState) -> bool:
    me = state.players[state.current]
    return in_dungeon(state) and not me.dungeon_locked and me.cash >= state.economy.dungeon_exit_cost


def send_to_dungeon(state: GameState) -> Step:
    """Straight to the dungeon, no salary on the way (D8)."""
    me = state.current
    state = update_player(state, me, position=dungeon_square(state), dungeon_turns=state.economy.dungeon_turns)
    return end_turn(replace(state, doubles=0)), (Event("sent_to_dungeon", me),)


def pay_exit(state: GameState) -> Step:
    me, cost = state.current, state.economy.dungeon_exit_cost
    state = update_player(change_cash(state, me, -cost), me, dungeon_turns=0, dungeon_locked=False)
    return state, (Event("left_dungeon", me, (("paid", cost), ("bank", -cost))),)


def stay_inside(state: GameState) -> Step:
    """A roll without a double: one round less inside, and the turn is over."""
    me = state.current
    left = state.players[me].dungeon_turns - 1
    state = update_player(state, me, dungeon_turns=left, dungeon_locked=state.players[me].dungeon_locked and left > 0)
    return end_turn(state), (Event("stayed_in_dungeon", me, (("left", left),)),)


def use_rope(state: GameState) -> Step:
    me = state.current
    cards = list(state.players[me].cards)
    cards.remove("rope")
    state = update_player(state, me, dungeon_turns=0, dungeon_locked=False, cards=tuple(cards))
    return state, (Event("used_rope", me),)
