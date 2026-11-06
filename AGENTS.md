# AGENTS.md -- instructions for AI coding agents working on Traveler Quartet

Read this first. It is short on purpose: the rules here are the ones that matter on every task. The project itself is
described in `README.md`, the rules of the game in `RULES.md`, the contribution terms in `CONTRIBUTING.md`.

## What this project is

A board game for 2-4 merchants in an isekai world, playable by humans, computer players and AI players. The rules
engine is the ARBITER: it knows the true state of the game, lists the legal actions, and refuses anything else. A
player -- human, bot or AI -- only ever chooses among legal actions. The game is also a measuring instrument: the engine
records what players DO, next to what they SAY (a free message attached to an action).

## Where things live

| folder | what | rule |
|---|---|---|
| `src/traveler_quartet/rules/` | the engine: `apply(state, action) -> (state, events)`, `legal_actions`, `actor`, `negotiations` | PURE functions, frozen state, no I/O, no randomness except the seeded dice |
| `src/traveler_quartet/data/` | the board, the economy (`economy.json`) and the cards, as DATA | an amount is changed here, never in code -- and a change of amount is a DECISION (see below) |
| `src/traveler_quartet/players/` | the computer players (`bots.py`, `hard.py`, `adaptive.py`), what one player may SEE (`view.py`), the state as text (`text.py`), the AI player by command (`command_player.py`) | a player is a function `(state, legal) -> action` or `(action, message)` |
| `src/traveler_quartet/match/` | the game loop (`runner.py`), the tournaments (`tournament.py`), a game SESSION for remote players (`session.py`), the local HTTP server (`server.py`, standard library, 127.0.0.1), the console game for a human (`console.py`) and a terminal client for ONE seat of the server (`seat.py`) | a front end talks ONLY to the server: create a game, read `/view` with its token, post to `/act` -- see the docstring of `server.py` |
| `tests/` | pytest; `factory.py` builds test states | mechanics tests use a rent of 10 % (simple numbers); `test_rules_amounts.py` pins the real amounts |

## The contract a front end must respect

A user interface (web page, console, stream overlay) shows `view(state, player)` and sends back ONE action from
`legal_actions` (or a full offer from `negotiations`). It never reads the state directly: the view hides the other
players' kept cards, their sealed bids, and the future (the order of the decks, the seed of the dice). A front end
that shows more than the view lets a player cheat.

## Testing the game as a player

To see what a player sees, play one seat yourself: start `traveler-quartet serve`, then one command per move with
`python -m traveler_quartet.match.seat new remote,normal,normal,normal <seed>`, then `view`, `act <action> [message]`,
`events [since]` (details in the docstring of `seat.py`). Report what reads badly or is missing.

- Such a game is a **UX test, never a result**: you know the code and the bots, so you are not a blind player. Say so
  in your report, and never quote its score as a measure of the game or of a player.
- While playing, read only what the seat shows: never the engine state, the decks, the seed or the bots' code.
- Measured games (who wins, do players trade) are played by `ai-game` or `tournament`, not by you at the table.

## How to talk with us

- **Keep a critical mind.** You are a peer engineer, not an assistant who agrees. If a request, a remark or an idea
  from the maintainer -- or from the other AI agent -- looks wrong, useless or harmful to the game, say **no**, plainly,
  and say why. A frank "this won't work because..." is worth more than polite compliance.
- **You can be wrong too.** Say what you are unsure of, separate what you checked from what you assume, and prefer a
  measure (a test, a tournament, a run) to an opinion. When you are corrected, check the correction, then change your
  mind or explain why not.
- No flattery, no validation theater: an honest disagreement is welcome here.

## How to work

1. **Before coding**: read the files you will touch and their tests; say which files you will change and why.
2. **Tests first**: write the test that the change must pass, see it fail, then write the code. A test must be able to
   fail: never a test that passes whatever the code does, never a test that only runs under a condition that is false.
3. **Check that the tests bite**: break the new code on purpose (one line at a time) and check a test fails.
4. **Run the whole suite**: `python -m pip install -e ".[dev]"` then `python -m pytest -q` -- green before any commit.
   CI runs it on Linux and Windows, Python 3.10 and 3.13.
5. **Report**: the files changed, what changed and why, the tests run, and what you did NOT verify.

## Code conventions

- English for every identifier, file name, comment and message. No emoji anywhere.
- Python 3.10 syntax only. No new dependency without asking.
- Files under 500 lines; small functions; at most two levels of nesting.
- Functional core, imperative shell: logic in pure functions, I/O at the edges.
- Errors are explicit: never an empty `except`, never a silent fallback that hides a failure.
- Keep the existing patterns; do not redesign a module without being asked.

## Rules you must not break

- **A rule or an amount of the game changes only by decision of the maintainer**, never as a side effect of a task.
  If a task seems to need one, stop and ask. When a rule changes, `RULES.md` changes in the SAME commit.
- **The engine stays the arbiter**: no shortcut that lets a player act outside `legal_actions`.
- **Never weaken the view**: no secret (kept cards, sealed bids, decks order, seed) may reach a player or a front end.
- **Work only inside this repository.** Never read, write or reference files outside it. Never write a path, a user
  name or an account name from this machine into the code, a commit or a document.
- **No secrets in the repository**: no API key, no `.env`, no game logs of real players.
- **Another AI agent also works on this repository.** Work on your own branch, one task per branch; do not rewrite or
  reformat files outside your task; never force-push; never commit to `main` directly -- open a pull request.
- **Ask before anything destructive** (deleting files, rewriting history, changing the CI).
