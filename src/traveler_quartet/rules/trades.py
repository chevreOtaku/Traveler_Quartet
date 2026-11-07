"""Trades (D21): talk is free, the CONTRACT is structured and checked by the engine. What each side receives is worth
between half and double what it gives; at most 3 counter-offers; on one's own turn; no district of a built town."""

from dataclasses import dataclass, replace
from typing import Optional, Tuple

from traveler_quartet.rules.state import Event, GameState, change_cash, set_at, update_player

MAX_COUNTERS, MAX_OFFERS_PER_TURN = 3, 3


@dataclass(frozen=True)
class Terms:
    give_gold: int = 0
    give_squares: Tuple[int, ...] = ()
    give_cards: Tuple[str, ...] = ()
    ask_gold: int = 0
    ask_squares: Tuple[int, ...] = ()
    ask_cards: Tuple[str, ...] = ()

    def swapped(self) -> "Terms":
        return Terms(self.ask_gold, self.ask_squares, self.ask_cards, self.give_gold, self.give_squares, self.give_cards)


@dataclass(frozen=True)
class Trade:
    proposer: int
    responder: int
    terms: Terms
    counters: int = 0


def _ints(text: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in text.split(",") if x)


def _names(text: str) -> Tuple[str, ...]:
    return tuple(x for x in text.split(",") if x)


def parse_terms(fields) -> Optional[Terms]:
    """Six fields: gold given, squares given, cards given, gold asked, squares asked, cards asked."""
    if len(fields) != 6:
        return None
    try:
        return Terms(int(fields[0] or 0), _ints(fields[1]), _names(fields[2]),
                     int(fields[3] or 0), _ints(fields[4]), _names(fields[5]))
    except ValueError:
        return None


def value_of(state: GameState, gold: int, squares: Tuple[int, ...], cards: Tuple[str, ...]) -> int:
    values = state.economy.card_values
    return gold + sum(state.board.squares[i].price for i in squares) + sum(values.get(c, 0) for c in cards)


def _can_hand_over(state: GameState, player: int, gold: int, squares: Tuple[int, ...], cards: Tuple[str, ...]) -> bool:
    me = state.players[player]
    if gold < 0 or gold > me.cash or len(set(squares)) != len(squares):
        return False
    held = list(me.cards)
    for card in cards:
        if card not in held:
            return False
        held.remove(card)
    return all(_tradable(state, player, i) for i in squares)


def _tradable(state: GameState, player: int, index: int) -> bool:
    if not 0 <= index < len(state.board.squares) or state.owners[index] != player:
        return False
    square = state.board.squares[index]
    return square.kind != "district" or not any(state.buildings[i] for i in state.board.towns[square.town])


def valid(state: GameState, giver: int, receiver: int, terms: Terms) -> bool:
    if receiver == giver or not 0 <= receiver < len(state.players) or state.players[receiver].out:
        return False
    given = value_of(state, terms.give_gold, terms.give_squares, terms.give_cards)
    received = value_of(state, terms.ask_gold, terms.ask_squares, terms.ask_cards)
    if given == 0 or not (given <= 2 * received and received <= 2 * given):
        return False
    return (_can_hand_over(state, giver, terms.give_gold, terms.give_squares, terms.give_cards)
            and _can_hand_over(state, receiver, terms.ask_gold, terms.ask_squares, terms.ask_cards))


def contract(trade: Trade) -> Tuple[Tuple[str, object], ...]:
    """The public payload of a trade event (contract v2): who proposes, who answers, and the terms from the PROPOSER's
    side (give = what the proposer gives). The same terms the view already shows while the offer is open."""
    t = trade.terms
    terms = {"give_gold": t.give_gold, "give_squares": list(t.give_squares), "give_cards": list(t.give_cards),
             "ask_gold": t.ask_gold, "ask_squares": list(t.ask_squares), "ask_cards": list(t.ask_cards)}
    return (("proposer", trade.proposer), ("responder", trade.responder), ("terms", terms))


def offer(state: GameState, receiver: int, terms: Terms) -> Tuple[GameState, Tuple[Event, ...]]:
    trade = Trade(proposer=state.current, responder=receiver, terms=terms)
    state = replace(state, pending="trade", trade=trade, offers=state.offers + 1)
    return state, (Event("offered", state.current, (("to", receiver),) + contract(trade)),)


def counter(state: GameState, terms: Terms) -> Tuple[GameState, Tuple[Event, ...]]:
    """A counter IS the new offer: the counterer becomes the proposer."""
    t = state.trade
    trade = Trade(proposer=t.responder, responder=t.proposer, terms=terms, counters=t.counters + 1)
    return replace(state, trade=trade), (Event("countered", t.responder, (("to", t.proposer),) + contract(trade)),)


def _hand_over(state: GameState, giver: int, receiver: int, gold: int, squares, cards) -> GameState:
    state = change_cash(change_cash(state, giver, -gold), receiver, gold)
    for i in squares:
        state = replace(state, owners=set_at(state.owners, i, receiver))
    for card in cards:
        mine = list(state.players[giver].cards)
        mine.remove(card)
        state = update_player(state, giver, cards=tuple(mine))
        state = update_player(state, receiver, cards=state.players[receiver].cards + (card,))
    return state


def accept(state: GameState) -> Tuple[GameState, Tuple[Event, ...]]:
    t = state.trade
    s = t.terms
    state = _hand_over(state, t.proposer, t.responder, s.give_gold, s.give_squares, s.give_cards)
    state = _hand_over(state, t.responder, t.proposer, s.ask_gold, s.ask_squares, s.ask_cards)
    accepted = Event("trade_done", t.responder, (("with", t.proposer),) + contract(t))
    return replace(state, pending="roll", trade=None), (accepted,)


def refuse(state: GameState) -> Tuple[GameState, Tuple[Event, ...]]:
    t = state.trade
    return replace(state, pending="roll", trade=None), (Event("trade_refused", t.responder, (("from", t.proposer),)),)
