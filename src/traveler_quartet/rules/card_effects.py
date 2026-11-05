"""What a card does. Each effect returns (state, events, next): `continue` (the move goes on), `land` (the player moved:
resolve the square he is on), `done` (the effect already set what comes next: a debt, a target, the end of the turn)."""

from dataclasses import replace
from typing import Callable, Dict, List, Tuple

from traveler_quartet.rules import finance
from traveler_quartet.rules.cards import Card, card_die, carousel, draw
from traveler_quartet.rules.disasters import (buildings_of, damage, destroy, owns_a_whole_pair, pay_what_he_can)
from traveler_quartet.rules.dungeon import send_to_dungeon
from traveler_quartet.rules.economy import STALL, owns_whole_town
from traveler_quartet.rules.income import start_income
from traveler_quartet.rules.state import Event, GameState, change_cash, update_player
from traveler_quartet.rules.turns import end_turn

Result = Tuple[GameState, Tuple[Event, ...], str]


def _card_event(state: GameState, card: Card, **data) -> Event:
    return Event("card", state.current, (("card", card["id"]),) + tuple(data.items()))


def _gain(state: GameState, player: int, amount: int) -> Tuple[GameState, Event]:
    return change_cash(state, player, amount), Event("paid_by_bank", player, (("amount", amount), ("bank", amount)))


def _pay(state: GameState, card: Card, amount: int) -> Result:
    me = state.current
    state = finance.charge(state, amount, None)
    if state.pending == "debt":
        return state, (_card_event(state, card), Event("debt_opened", me, (("to", "bank"), ("amount", amount)))), "done"
    return state, (_card_event(state, card), Event("paid_to_bank", me, (("amount", amount), ("bank", -amount)))), "continue"


def _active_others(state: GameState) -> List[int]:
    return [p for p in range(len(state.players)) if p != state.current and not state.players[p].out]


def gain(state, card):
    state, event = _gain(state, state.current, card["amount"])
    return state, (_card_event(state, card), event), "continue"


def pay(state, card):
    return _pay(state, card, card["amount"])


def nothing(state, card):
    return state, (_card_event(state, card),), "continue"


def everyone_gains(state, card):
    events = [_card_event(state, card)]
    for p in [state.current] + _active_others(state):
        state, event = _gain(state, p, card["amount"])
        events.append(event)
    return state, tuple(events), "continue"


def die(state, card):
    town = carousel(state) if card.get("carousel") else None
    state, face = card_die(state)
    amount = card["even"] if face % 2 == 0 else card["odd"]
    head = _card_event(state, card, die=face, town=town)
    if amount > 0:
        state, event = _gain(state, state.current, amount)
        return state, (head, event), "continue"
    if amount < 0:
        state, events, nxt = _pay(state, card, -amount)
        return state, (head,) + events[1:], nxt
    return state, (head,), "continue"


def _buildings(state: GameState, player: int) -> int:
    return sum(min(level, 1) if level == STALL else level
               for i, level in enumerate(state.buildings) if state.owners[i] == player)


def pay_per_building(state, card):
    return _pay(state, card, card["amount"] * _buildings(state, state.current))


def collect_from_others(state, card):
    events = [_card_event(state, card)]
    for p in _active_others(state):
        state, paid = pay_what_he_can(state, p, card["amount"])
        state = change_cash(state, state.current, paid)
        events.append(Event("paid_to_player", p, (("to", state.current), ("amount", paid))))
    return state, tuple(events), "continue"


def move_back(state, card):
    me = state.current
    position = (state.players[me].position - card["steps"]) % len(state.board.squares)
    return update_player(state, me, position=position), (_card_event(state, card),), "land"


def move_to_start(state, card):
    me = state.current
    income = start_income(state, me)
    state = update_player(change_cash(state, me, income), me, position=0, jump_ready=True)
    return state, (_card_event(state, card), Event("passed_start", me, (("amount", income), ("bank", income)))), "land"


def go_to_dungeon(state, card):
    state, events = send_to_dungeon(state)
    return state, (_card_event(state, card),) + events, "done"


def you_pay_others_gain(state, card):
    events = [_card_event(state, card)]
    for p in _active_others(state):
        state, event = _gain(state, p, card["each"])
        events.append(event)
    state, paid, nxt = _pay(state, card, card["you"])
    return state, tuple(events) + paid[1:], nxt


def keep(state, card):
    me = state.current
    state = update_player(state, me, cards=state.players[me].cards + (card["id"],))
    return state, (_card_event(state, card),), "continue"


def invention(state, card):
    first = card["id"] not in state.discovered
    if first:
        state = replace(state, discovered=state.discovered + (card["id"],))
    events = [_card_event(state, card, first=first)]
    for p in range(len(state.players)):
        if state.players[p].out:
            continue
        owned = sum(owns_whole_town(state.board, state.owners, town, p) for town in card["pair"])
        amount = card["both"] if owned == 2 else card["one"] if owned == 1 else 0
        if amount:
            state, event = _gain(state, p, amount)
            events.append(event)
    return state, tuple(events), "continue"


def disaster(state, card):
    town = carousel(state)
    state, face = card_die(state)
    state, hit = destroy(state, town, damage(face), card["target"])
    head = _card_event(state, card, town=town, die=face)
    return state, (head, Event("disaster", state.current, (("town", town), ("destroyed", len(hit))))), "continue"


def repair(state, card):
    town = carousel(state)
    built = [i for i in state.board.towns[town] if state.buildings[i] > 0]
    events = [_card_event(state, card, town=town)]
    if built:
        owner = state.owners[built[0]]
        cost = state.economy.house_costs[town] * card["percent"] // 100
        state, paid = pay_what_he_can(state, owner, cost)
        events.append(Event("paid_to_bank", owner, (("amount", paid), ("bank", -paid))))
    return state, tuple(events), "continue"


def crisis_on(state: GameState, player: int, towns: Tuple[str, ...], per_building: int) -> Tuple[GameState, Event]:
    due = buildings_of(state, player, towns) * per_building
    if any(owns_a_whole_pair(state, player, town) for town in towns):
        due = due * 3 // 2
    state, paid = pay_what_he_can(state, player, due)
    return state, Event("crisis", player, (("amount", paid), ("bank", -paid)))


def crisis(state, card):
    events = [_card_event(state, card, town=card["town"])]
    owners = {state.owners[i] for i in state.board.towns[card["town"]]} - {None}
    for owner in sorted(owners):
        state, event = crisis_on(state, owner, (card["town"],), card["amount"])
        events.append(event)
    return state, tuple(events), "continue"


def festival(state, card):
    events = [_card_event(state, card, town=card["town"])]
    owners = {state.owners[i] for i in state.board.towns[card["town"]]} - {None}
    for owner in sorted(owners):
        state, event = _gain(state, owner, card["amount"])
        events.append(event)
    return state, tuple(events), "continue"


def curse(state, card):
    state, face = card_die(state)
    head = _card_event(state, card, die=face)
    if face % 2 == 0:
        state, kept, _ = keep(state, card)
        return state, (head,), "continue"
    return replace(state, pending="target"), (head,), "done"


def lose_turn_then_free(state, card):
    state = update_player(state, state.current, dungeon_turns=0, dungeon_locked=False)
    return end_turn(state), (_card_event(state, card),), "done"


def free_exit(state, card):
    state = update_player(state, state.current, dungeon_turns=0, dungeon_locked=False)
    return state, (_card_event(state, card),), "continue"


def lock(state, card):
    return update_player(state, state.current, dungeon_locked=True), (_card_event(state, card),), "continue"


def draw_event(state, card):
    state, events, nxt = resolve(state, "event")
    return state, (_card_event(state, card),) + events, nxt


EFFECTS: Dict[str, Callable[[GameState, Card], Result]] = {
    "gain": gain, "pay": pay, "nothing": nothing, "everyone_gains": everyone_gains, "die": die,
    "pay_per_building": pay_per_building, "collect_from_others": collect_from_others, "move_back": move_back,
    "move_to_start": move_to_start, "go_to_dungeon": go_to_dungeon, "you_pay_others_gain": you_pay_others_gain,
    "keep": keep, "invention": invention, "disaster": disaster, "repair": repair, "crisis": crisis,
    "festival": festival, "curse": curse, "lose_turn_then_free": lose_turn_then_free, "free_exit": free_exit,
    "lock": lock, "draw_event": draw_event,
}


def resolve(state: GameState, deck: str) -> Result:
    state, card = draw(state, deck)
    return EFFECTS[card["effect"]](state, card)
