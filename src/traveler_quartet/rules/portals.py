from traveler_quartet.rules.income import start_income
from traveler_quartet.rules.moves import moved
from traveler_quartet.rules.state import Event, GameState, Step, change_cash, update_player
from traveler_quartet.rules.turns import finish


def next_portal(state: GameState, index: int) -> int:
    size = len(state.board.squares)
    return next((index + k) % size for k in range(1, size) if state.board.squares[(index + k) % size].kind == "portal")


def can_jump(state: GameState) -> bool:
    me = state.players[state.current]
    return me.jump_ready and state.board.squares[me.position].kind == "portal"


def jump(state: GameState) -> Step:
    """Jump to the next portal: nothing happens there. One jump per lap; a jump across Start pays the Start income but
    also uses the next lap's jump (D17)."""
    me = state.current
    origin = state.players[me].position
    target = next_portal(state, origin)
    state = update_player(state, me, position=target, jump_ready=False)
    events = [Event("jumped", me, (("from", origin), ("to", target))), *moved(me, origin, target, "portal", None)]
    if target < origin:
        income = start_income(state, me)
        state = change_cash(state, me, income)
        events.append(Event("passed_start", me, (("amount", income), ("bank", income))))
    return finish(state), tuple(events)


def stay(state: GameState) -> Step:
    return finish(state), (Event("stayed", state.current),)
