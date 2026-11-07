"""The public MOVEMENT event (contract v2, agreed with the front, 07/11) -- one `moved` per real movement.

`travel` says HOW: a `walk` along the board with SIGNED `steps` (forward > 0, back < 0), or a `teleport` (`steps` None).
`kind` says WHY: `dice`, `card`, `portal`, `dungeon`. The front animates `moved` only; it never infers a direction.
A movement that ends where it started is not a movement: no event is fabricated.
"""

from typing import Optional, Tuple

from traveler_quartet.rules.state import Event


def moved(player: int, origin: int, target: int, kind: str, steps: Optional[int]) -> Tuple[Event, ...]:
    """The `moved` event, or nothing when the player did not move. `steps` None = a teleport."""
    if origin == target:
        return ()
    travel = "teleport" if steps is None else "walk"
    return (Event("moved", player, (("from", origin), ("to", target), ("kind", kind), ("travel", travel),
                                    ("steps", steps))),)
