"""What a district or a house is WORTH to a player, read from the numbers of the rules (decision D42) -- pure.

The Hard computer was written for the rules as they are (it buys everything because, today, a district counts at its full
price at the end). When the rules change, it keeps playing for the old ones. Here every value is computed from the rules
themselves: the rent still to collect before the end (where pawns land, how many rivals, how many rounds are left) and
what the purchase will count for in the final ranking.
"""

from traveler_quartet.players.landing import landing_frequencies
from traveler_quartet.rules.buildings import house_cost
from traveler_quartet.rules.economy import rent
from traveler_quartet.rules.state import GameState, set_at

ROLLS_PER_TURN = 1 + 1 / 6 + 1 / 36     # a double rolls again, three in a row stop


def rounds_left(state: GameState) -> int:
    return max(state.economy.rounds - state.round, 0)


def _rivals(state: GameState, me: int) -> int:
    return sum(1 for p, player in enumerate(state.players) if p != me and not player.out)


def expected_hits(state: GameState, square: int, me: int) -> float:
    """How many times rivals should land on `square` before the end."""
    return landing_frequencies(state.board)[square] * ROLLS_PER_TURN * _rivals(state, me) * rounds_left(state)


def end_value(state: GameState, amount: int) -> float:
    return amount * state.economy.final_value_percent / 100


def _rent(state: GameState, owners, buildings, square: int) -> int:
    return rent(state.board, state.economy, owners, square, buildings, state.mortgaged)


def _town_lift(state: GameState, square: int, me: int) -> float:
    """The extra rent the OTHER districts of the town earn once `square` completes it."""
    town = state.board.squares[square].town
    others = [i for i in state.board.towns.get(town, ()) if i != square]
    if not town or any(state.owners[i] != me for i in others):
        return 0.0
    after = set_at(state.owners, square, me)
    return sum(expected_hits(state, i, me) * (_rent(state, after, state.buildings, i)
                                               - _rent(state, state.owners, state.buildings, i)) for i in others)


def worth(state: GameState, square: int, me: int) -> float:
    """What owning `square` brings `me` from now to the end: its rents, the lift of a completed town, its final value."""
    owned = set_at(state.owners, square, me)
    rents = expected_hits(state, square, me) * _rent(state, owned, state.buildings, square)
    return rents + _town_lift(state, square, me) + end_value(state, state.board.squares[square].price)


def buy_gain(state: GameState, square: int, me: int) -> float:
    return worth(state, square, me) - state.board.squares[square].price


def house_gain(state: GameState, square: int) -> float:
    """One more house on `square`: the extra rent before the end and its final value, minus what it costs."""
    me, cost = state.owners[square], house_cost(state, square)
    higher = set_at(state.buildings, square, state.buildings[square] + 1)
    extra = _rent(state, state.owners, higher, square) - _rent(state, state.owners, state.buildings, square)
    return expected_hits(state, square, me) * extra + end_value(state, cost) - cost
