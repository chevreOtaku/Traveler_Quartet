"""What ONE player may see of a game (step 7, D34) -- pure. The same view for a human, a computer or an AI.

Hidden: the OTHERS' kept cards (only how many -- the karma mirror is secret), the others' sealed bids, and the FUTURE --
the order of the decks and the seed the dice come from (an AI shown them could cheat without meaning to). Everything else
on the table is public. The legal actions are given only to the player who must answer.
"""

from typing import Dict, List

from traveler_quartet.rules.engine import actor, legal_actions, negotiations
from traveler_quartet.rules.state import GameState


def _square(state: GameState, i: int) -> Dict[str, object]:
    s = state.board.squares[i]
    return {"index": i, "name": s.name, "kind": s.kind, "town": s.town, "price": s.price, "owner": state.owners[i],
            "buildings": state.buildings[i], "mortgaged": state.mortgaged[i]}


def _player(state: GameState, p: int, mine: bool) -> Dict[str, object]:
    pl = state.players[p]
    out = {"seat": p, "cash": pl.cash, "position": pl.position, "out": pl.out, "in_dungeon": pl.dungeon_turns > 0,
           "cards_held": len(pl.cards)}
    return {**out, "cards": list(pl.cards)} if mine else out


def _sealed(state: GameState, me: int) -> Dict[str, object]:
    s = state.sealed
    out = {"square": s.square, "bids_written": len(s.bids)}
    if me in s.bidders and s.bidders.index(me) < len(s.bids):
        out["my_bid"] = s.bids[s.bidders.index(me)]
    return out


def _negotiation(state: GameState) -> Dict[str, object]:
    out: Dict[str, object] = {}
    if state.auction is not None:
        a = state.auction
        out["auction"] = {"square": a.square, "price": a.price, "leader": a.leader, "bidders": list(a.bidders)}
    if state.trade is not None:
        t = state.trade
        out["trade"] = {"proposer": t.proposer, "responder": t.responder, "counters": t.counters, "terms": t.terms.__dict__}
    if state.stall_request is not None:
        out["stall_request"] = list(state.stall_request)
    return out


def view(state: GameState, me: int) -> Dict[str, object]:
    turn = actor(state) == me and not state.over
    seen: Dict[str, object] = {
        "round": state.round, "rounds": state.economy.rounds, "current": state.current, "pending": state.pending,
        "last_dice": list(state.last_dice), "jackpot": state.jackpot, "houses_left": state.houses_left,
        "stalls_left": state.stalls_left, "me": _player(state, me, True),
        "others": [_player(state, p, False) for p in range(len(state.players)) if p != me],
        "board": [_square(state, i) for i in range(len(state.board.squares))],
        "your_turn": turn, "legal_actions": list(legal_actions(state)) if turn else [],
        "negotiations": list(negotiations(state)) if turn else [], **_negotiation(state)}
    if state.debt is not None and state.current == me:
        seen["debt"] = state.debt.amount
    if state.sealed is not None:
        seen["sealed"] = _sealed(state, me)
    return seen
