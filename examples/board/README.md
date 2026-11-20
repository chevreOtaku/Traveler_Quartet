# Connected board preview

A forty-square 2D board for the real local game, following the purchase-scene study.
No new dependency or build tool. From the repository root:

```text
python examples/board/serve.py
```

Open http://127.0.0.1:8878/ and start a game. Optional: --port 8879.
Choose 1-3 computer opponents and 5, 10 or 30 rounds.
The launcher serves a fixed list of front-end assets and delegates every game request
to the existing match.server handler. It neither reads GameState nor implements rules.
The original packaged text page and production server files are unchanged.

Click a square to inspect its deed and town. Legal actions, the private hand, trades,
sealed bids, debt and final ranking use the authorized player view.
Messages travel with the next action. The journal displays server sentences as text.
Gold, rents, multipliers and outcomes are supplied by the engine.

The public-view link contains a game ID only. It opens a separate read-only view,
using /public and /public/events without a player token.
Player tokens stay in headers and this tab's sessionStorage, never in URLs.
Reload resumes the seat while this preview server remains alive. After a server restart,
the old game is gone; select New game. Opening a player URL in a tab without its seat
offers a public-view link, rather than another player's private view.

## Current limits

This is a local development preview, not the release's packaged launcher.
The one merchant illustration is provisional; numbered/color-coded markers distinguish
players while the six final chibis are pending. Square details are also available by
keyboard. Small square names are supplementary; the selected deed carries the full name.

Positions snap to confirmed snapshots. No route is guessed and no movement animation is
enabled before the movement-event contract is implemented and reviewed.
The client bounds event consumption by the snapshot's log_length even when the current
server ignores the future until parameter. Later events wait for the next snapshot.

If revision is supplied, the client sends expected_revision with its action. With the
current pre-synchronization server it refreshes and compares the question before sending;
this cannot close the final server-side race. Atomic stale-action protection awaits the
agreed session revision work. Failed actions are never retried automatically.
No actual OBS/GPU performance claim is made by these local browser checks.

## Reference study

The older zhongyi-tong/monopoly project informed the idea of a focused decision panel,
public messages and staged movement presentation. No source or asset was imported.
Its always-forward movement and continuous 3D render loop are not used. This board uses
native HTML/CSS and reads the current game's HTTP contracts, not that project's rules.

## Checks

```text
node --test
python -m pytest -q
```

The manual browser play is a UX test, not an evaluation of strategy or balance.
No API model calls or new scheduled service are introduced.
