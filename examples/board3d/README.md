# Merchant movement study

Lot 1: one original chibi merchant made from three.js primitives, a ten-square
section of the public board, and one actual computer move. This is an offline
visual study, not a connected game client or a measurement of player performance.

From the repository root, with the project's Python available:

```sh
python examples/board3d/make_fixture.py
python examples/board3d/serve.py
```

Open `http://127.0.0.1:8879`. Use `--port 0` for a free port; the server prints
its URL. The fixture must be generated before replaying. A missing fixture is
reported on the page; no synthetic journey replaces it. ES modules require HTTP.

The generator plays four normal computers from a fixed seed, without modifying
the state or the rules. It stops after one action containing a single walk of
two to eight squares, and writes only `watched` snapshots before/after and the
`public_events` interval between their log watermarks. The seed, state, private
hands and tokens are never exported. Regenerate after engine changes.

The client reads signed `steps`, `from`, `to`, `travel`, and `kind` from `moved`
v2. Forward and backward walks visit each supplied step; teleports have no walk.
Malformed contracts fail explicitly. Other events do not drive movement.
The ten displayed squares are a study layout in public board order, with names
from the fixture, not a proposed complete board layout. Only the moving player
is represented. Replay resets that same recorded move; it does not roll again.

Use **Replay the move** and **Inspect figurine**. Detail follows the merchant,
including during replay. Check the page at 1920 x 1080 and 1280 x 720; inspect the
eyes, head/body proportions, apron, satchel, glossy highlights, faceted terrain,
soft shadow and each landing. Labels also appear in the expandable text list.
With system reduced motion enabled, replay places the pawn directly at arrival.
Changing the preference during a hop also ends the animation directly.

Rendering is requested on resize, view changes, visibility changes and movement.
There is no idle animation, orbit control, automatic replay or perpetual frame
loop. Three lights: hemisphere, key directional (the only shadow caster), and
fill directional. PCF soft shadows, ACES, sRGB output, 60-degree perspective.
All artwork is original code. No Clawblox code or assets are used. The sole
dependency is the existing unmodified local three.js 0.170.0 module and its MIT
license in `examples/vendor/three/`. No CDN, model, font or external texture.

Checks from the repository root:

```sh
node --test tests/board3d.test.cjs
python -m pytest -q tests/test_board3d_fixture.py
python -m pytest -q
```
