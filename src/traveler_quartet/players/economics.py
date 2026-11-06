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
BUILT_LEVEL = 3                         # the potential of a town: whole, three houses on each district
REALISED_SHARE = 0.5                    # completing and building take time: half the rounds left earn it


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


def town_potential(state: GameState, town: str, owner: int) -> float:
    """E19 : what a town would bring `owner` if he held it WHOLE with three houses on each district -- the extra rent
    over the bare one (on the share of the rounds left it would take to get there), minus the houses, plus their final
    value. The real value of a district lives HERE, not in its bare rent."""
    squares = state.board.towns[town]
    owners = tuple(owner if i in squares else o for i, o in enumerate(state.owners))
    built = tuple(BUILT_LEVEL if i in squares else b for i, b in enumerate(state.buildings))
    houses = sum(BUILT_LEVEL * house_cost(state, i) for i in squares)
    extra = sum(expected_hits(state, i, owner) * (_rent(state, owners, built, i) - _rent(state, state.owners, state.buildings, i))
                for i in squares)
    return REALISED_SHARE * extra - houses + end_value(state, houses)


def _closer(k: int, n: int) -> float:
    """How much one more district of a town (from k to k + 1 of n) brings it closer to whole: quadratic -- the last one
    matters most."""
    return ((k + 1) / n) ** 2 - (k / n) ** 2


def option_value(state: GameState, square: int, me: int) -> float:
    """My share of the town's potential -- none if a rival already holds part of it (no completion without a trade)."""
    town = state.board.squares[square].town
    others = [state.owners[i] for i in state.board.towns.get(town, ()) if i != square]
    if not town or any(o not in (None, me) for o in others):
        return 0.0
    return max(town_potential(state, town, me), 0.0) * _closer(others.count(me), len(others) + 1)


def block_value(state: GameState, square: int, me: int) -> float:
    """What I deny the ONE rival who holds the rest of the town, if he is the only other owner there."""
    town = state.board.squares[square].town
    others = {state.owners[i] for i in state.board.towns.get(town, ()) if i != square} - {None}
    if not town or len(others) != 1 or me in others:
        return 0.0
    rival = others.pop()
    held = sum(1 for i in state.board.towns[town] if state.owners[i] == rival)
    return max(town_potential(state, town, rival), 0.0) * _closer(held, len(state.board.towns[town]))


def worth(state: GameState, square: int, me: int) -> float:
    """What owning `square` brings `me` from now to the end: its rents, the lift of a completed town, its OPTION on the
    town and what it BLOCKS (E19), its final value."""
    owned = set_at(state.owners, square, me)
    rents = expected_hits(state, square, me) * _rent(state, owned, state.buildings, square)
    return (rents + _town_lift(state, square, me) + option_value(state, square, me) + block_value(state, square, me)
            + end_value(state, state.board.squares[square].price))


def buy_gain(state: GameState, square: int, me: int) -> float:
    return worth(state, square, me) - state.board.squares[square].price


def house_gain(state: GameState, square: int) -> float:
    """One more house on `square`: the extra rent before the end and its final value, minus what it costs."""
    me, cost = state.owners[square], house_cost(state, square)
    higher = set_at(state.buildings, square, state.buildings[square] + 1)
    extra = _rent(state, state.owners, higher, square) - _rent(state, state.owners, state.buildings, square)
    return expected_hits(state, square, me) * extra + end_value(state, cost) - cost
