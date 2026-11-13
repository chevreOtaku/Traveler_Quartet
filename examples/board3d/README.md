# Four miniature merchants / public board

Lot 2 builds the full forty-square ring, four provisional merchants, and a
spectator client for the existing local game server. All geometry is original
three.js code. This is a UX study, not a measurement of strategy or balance.

## Launch

From the repository root, with the project's Python environment available:

```sh
python examples/board3d/serve.py
```

Open `http://127.0.0.1:8879/`, then select **Watch four computers**. Choose an
integer seed and 5, 10 or 30 rounds. The launcher uses `make_server`, serves only
the listed local assets, and delegates all game requests to the existing server.
Use `--port 0` for a free port; the launcher prints the URL. No separate static
server, build step, API key, token or external resource is needed.

The current server computes an entire all-computer game during `POST /games`.
The page then replays that game's actual public journal in order. It does not
pace the engine, generate rolls, or manufacture intermediate snapshots. Creating
a game can therefore take time before playback starts. **Go to latest** finishes
the presentation immediately. **Replay / retry** reads and replays the journal
again. A genuinely live paced computer match would need a server contract that
advances computer actions incrementally; no such endpoint is assumed here.

Enter an existing game ID, or open `/?game=<id>`, to show its current public
snapshot and follow new revisions every 1.5 seconds. The game must belong to this
preview server instance. Polling stops after the final snapshot and its journal
have both been consumed. The viewer never sends player actions.

## Public transport and animation

The client reads `/games/<id>/public`, then
`/games/<id>/public/events?since=a&until=b`, without authorization headers.
`a` is included; `b` is excluded and equals that snapshot's `log_length`.
Future rows stay outside the interval. Indexes must be contiguous; revisions
must be ordered and bounded by the snapshot. An eventless revision still updates
the table. Only one fetch/playback transaction runs at a time.

Before animating, the client reverses the interval's `moved` v2 events from the
snapshot's public positions and checks continuity. It never assumes that players
started at Start. During playback, each event completes before the next starts;
the confirmed snapshot is applied last. Balances and final dice are not presented
as historical intermediate values. Dice during replay come from `rolled` events.

Forward and backward walks use the supplied signed `steps`, including wraps and
multiple laps. Teleports place the pawn directly at arrival. Other events do not
move pawns. A missing index, invalid revision, bad movement or inconsistent
position discards the interval, reads a fresh public snapshot, resets the scene,
and reports the skipped interval. Network errors preserve the cursor for retry.

## Scale and display

The previous sculpt measured 3.197 high with a 2.020 by 1.614 footprint in world
units, on hexagonal tiles of diameter 2.08. The finished miniature, including its
base, is now exactly 0.700 high and fits a 0.420 by 0.420 envelope. Square pitch
is 1; the visible tile is 0.98 wide. Each seat has a fixed offset of +/-0.25 on
both axes, leaving 0.08 between neighboring envelopes. The sculpt is uniformly
scaled, preserving the large head, eyes and glossy materials.

The base has a raised number and a distinct outline: 0 circle, 1 triangle,
2 square, 3 diamond, plus colour. Eliminated players disappear at their public
bankruptcy event or confirmed snapshot. **Inspect figurine** isolates the chosen
seat with a close 60-degree perspective camera. During movement it follows the
moving seat. **Return to board** restores the whole ring.

The board uses an orthographic overview, numbered tiles, town colour bands and
eight numbered town keys. Names come from the public board and use 18 px HTML
callouts with leader lines. The centre contains the public dice and current event.
Below 1420 px wide the board scrolls horizontally, preserving label size. Full
name wrapping and visual clearance need a real browser check at 1920 x 1080;
the Node projection test is not a screenshot check. No dressed cities, six final
merchants, human controls or actual OBS integration are included.

Rendering occurs on resize, view changes, visibility changes and movement, with
no perpetual frame loop or idle animation. System reduced motion places each
merchant directly at arrival, including when enabled during a hop. Three lights,
one shadow caster, PCF soft shadows, ACES and sRGB are retained. The dependency is
the existing unmodified module and MIT license in `examples/vendor/three/`.
No CDN, model, font, external texture or other game's assets are used.

## Fixture and checks

`http://127.0.0.1:8879/?mode=fixture` replays the retained Lot 1 fixture with all
four pawns on the full ring. Regenerate it only when required by engine changes:

```sh
python examples/board3d/make_fixture.py
```

The generator exports only public before/after snapshots and their bounded event
interval. Kept cards, sealed bids, deck order, tokens and engine state stay out.

```sh
node --test
python -m pytest -q tests/test_board3d_fixture.py
python -m pytest -q
```

Node checks cover real merchant bounds, four-seat separation, ring adjacency,
queue ordering, journal resynchronization, retries, page controls, reduced motion
and scene projection. The renderer and DOM in these tests are doubles; GPU output
is not verified. Python integration checks exercise `make_server`, four computer
seats and exclusive public event bounds. Python and real browser checks must run
in the maintainer's environment before committing this lot.
