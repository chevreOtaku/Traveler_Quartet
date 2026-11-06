# Traveler Quartet

*A light-hearted property-trading board game for 2 to 4 players, humans and AI, set in a world where people keep
getting isekai'd.*

> **Status: construction.** The rules engine plays complete games: buying, rent, houses and market stalls, pairs,
> portals, the dungeon, the three decks of cards, auctions, trades, shared stalls, mortgages, debt and bankruptcy.
> Computer players play tournaments, and command-line AI agents can join a mixed table. There is no web page yet. Every rule,
> name and amount may still change after the playtests.

```
python -m pip install -e ".[dev]"
python -m pytest
python -m traveler_quartet tournament --games 100
```

## The idea

Heroes from other worlds keep falling into this one, with their strange modern knowledge. **You are not one of
them.** You are an ordinary traveling merchant, born here. You go from town to town, buy districts, build them up
into market stalls, and try to end the game as the richest merchant of the realm.

The isekai part is the **setting**, not extra complexity. It lives in the names, the art and the card texts. The
rules stay as simple as the classic family property game, and the tone of the cards is absurd on purpose.

## At a glance

| | |
|---|---|
| Players | 2 to 4, any mix of humans, AI players and computer players |
| Length | **30 rounds**; the richest player wins (cash + value of districts and buildings) |
| Board | 40 squares, 4 sides, **8 towns**, 22 districts |
| Platform | a Python rules engine served to a light web page on `localhost`; multiplayer on a private server later |
| Pawns | 8 cute chibi merchants: human, elf, dwarf and orc, each as a man and a woman |
| Languages | English, with a French translation |

## The board

Each color is a small **town** with a trade, and each property card is a **district** of that town. The board follows
an economy: cheap raw materials at the start, luxury and money at the end.

| color | town | trade | districts |
|---|---|---|---|
| brown | Greenhorn Fields | farming, the town where beginners start | Cabbage Row · Newcomer's Gate |
| light blue | Overtime Hollow | the mine and its jewelers | Unpaid Shaft · Night Shift Tunnel · Gem Cutters' Lane |
| purple | Three Altars | three rival religions | Fountain of the Weeping Goddess · Chapel of the Made-Up God · Church of the Holy Nap |
| orange | Wildmark | hunting and fishing | Hunter's Rest · Fishmongers' Pier · Barbarian's Butchery |
| red | Glimmerland | the amusement park | Dragon-Go-Round · Mascot Avenue · Fireworks Square |
| yellow | Curtain Call | theater and entertainment | Villains' Stage · Bards' Corner · Puppet Lane |
| green | Wolfcoin | banks and moneychangers | Moneychangers' Street · Guild of Weighed Coins · Harvest Vault |
| dark blue | Royal Ziggurat | the capital: beauty and care, the richest town and the most exposed | Royal Bathhouse · Perfumers' Terrace |

**Pairs.** Towns come in pairs. Own both whole towns of a pair and you earn **+10 every time you pass Start** (the
base salary is 100).

| pair | towns |
|---|---|
| Food | Greenhorn Fields + Wildmark |
| Money & Leisure | Wolfcoin + Glimmerland |
| Luxury | Overtime Hollow + Royal Ziggurat |
| Culture | Three Altars + Curtain Call |

## Market stalls and partnerships

Market stalls replace hotels. You build one after **3 houses** on a district (houses and stalls are in limited
supply).

- A stall on your own district earns you **+20 each time you pass Start**.
- **Partnerships.** A rival can build a stall on your district, with your agreement, once you own the whole town. You
  each pay **half** the stall (your 3 houses stay yours), and you each earn **+10 when you pass Start**. That's all:
  the rent stays with the district's owner.
- **One partner per pair**, so the game doesn't turn into a web of schemes.
- **Breaking up.** To mortgage a district that carries your partner's stall, you must first refund their half, like
  a guarantor would. The stall goes, and so does the alliance.

## Special squares

| square | what happens |
|---|---|
| **Portals** (4) | Truck Portal, Summoning Circle, Rift Gate, Lost Hero's Door. Pay the portal's rent, then you **may jump to the next portal** (nothing happens where you land). One jump per lap; a jump across Start pays your salary but uses up the next lap's jump too. |
| **Dungeon** | Replaces jail. The *Go to the Dungeon* corner, a card, or three doubles in a row sends you there. You spend 2 rounds on a forced adventure (and still collect your rents). Leave early by paying, by drawing an Adventurer card, or by rolling a double. |
| **Lottery** | Taxes fill a jackpot; land on the park square to win it. |
| **Chance** (3) | Gains, losses and silly cards. |
| **Event** (2) | The world moves: inventions, disasters, crises, and one rare curse. |
| **Tax** (3) | Pay up. The money goes to the lottery. |
| **Utilities** | Endless Spring Waterworks Co. ("open 25 hours a day") and Mana Stone Mining Inc. ("unpaid overtime, guaranteed mana"). Rent is a dice roll times a multiplier. |

Portal rent only goes up if you own **all four**. Mortgages exist; auctions don't (for now). A bankrupt player is out
and the game goes on. Prices start at half the classic ones, since the salary is 100 gold, then playtests adjust them.

## The world moves (Event cards)

- **Inventions.** The first time an invention comes out, the realm discovers it ("the invention of mayonnaise").
  When it comes back, it becomes a wave of demand. The owner of one town of the matching pair earns +25, the owner of
  both earns +50.
- **Disasters.** A carousel picks a town at random, then a die decides the damage: even, nothing; 1, one house; 3, two
  houses; 5, three houses. Mindless disasters (earthquakes, monsters, a strange liquid spilled by a certain mining
  company) hit houses at random. Intelligent ones (a demon invasion, a riot led by a self-proclaimed water goddess) go
  for the most expensive houses. A stampede of flying cabbages only costs a repair. There is no insurance in this
  world.
- **Crises.** They hit a trade (an epidemic hits the capital). If you own the whole pair, both towns are hit, at
  x1.5 the cost.
- **The rare curse.** Play it on another player. Roll a die: even, you may keep it for later; odd, you must play it
  now. Alliances against the leader are part of the game.

## A taste of the cards

- *It's everyone's birthday! The Adventurers' Guild gives every player 100.*
- *A friendly slime ate your purse.* Even: it gives you a golden dropping, +100. Odd: it's a friendly slime, it
  doesn't pay back, −20.
- *You help a villager. To thank you, he gives you a giant white radish wearing tights.* It is of no use to you.
- *A mage is practicing: a giant explosion echoes over a distant town.* Even: a giant chest appears, +100. Odd: a
  meteor lands on your goods, −30.
- *(Dungeon) A mimic eats your clothes. An elf mage dressed all in white saves you.* −10.

## Built for AI players too

The rules engine offers every player, human or AI, the same list of **legal actions** as structured data, so any
program or language model can play through the same interface as a person. We also plan to record what AI players
**say** against what they **do**, and what they claim against the real state of the game.

Before any AI joins, three levels of computer players (Easy, Normal, Hard) play thousands of games against each
other to test the balance: game length, how often houses get built, and whether luck or skill wins:

```
traveler-quartet tournament --games 1000 --seats hard,normal,normal,normal [--no-disasters]
```

To play yourself in the console, against computer players:

```
traveler-quartet cli --opponents normal,normal,normal [--seed 7] [--rounds 10]
```

To play over the network of your own machine (the base of the coming web page and of AI players at a distance):

```
traveler-quartet serve            # http://127.0.0.1:8765 -- POST /games, then GET /view and POST /act with your token
```

The seats rotate from one game to the next. The amounts are not balanced yet: these tournaments are how we will
balance them.

### Play a mixed AI table

With the `claude` and `codex` commands installed and signed in:

```
python -m traveler_quartet ai-game --seats claude,codex,normal,normal --rounds 10 --seed 1
```

The agents use their existing command-line subscriptions. Each real choice starts a new agent invocation, so a game
can take several minutes and uses those accounts' limits. Computer seats can be `easy`, `normal`, `hard` or `adaptive`.
Two to four players are required. Without `--rounds`, the normal 30-round limit applies; the example is a short pilot.

The command prints a JSON report and its log path. The default log goes to the system temporary directory. An explicit
`--log` path must be outside every Git repository and must not already exist. The report includes AI decision journals,
table messages, trade/auction/curse counts by seat, retries, fallbacks, duration and the final ranking. Process failures
and empty command output stop the run with an error; they are not presented as AI decisions. Invalid decisions are
handled by the existing retry and logged safe-action policy. Automated tests use scripted commands, never real agents.
If an agent fails after play starts, the command saves a partial report before exiting non-zero: previous decisions
and messages, the failing round and seat, and the error. Its ranking is marked provisional. This handles reported
exceptions; it does not guarantee recovery from a killed process or a disk failure, and it does not resume the game.

## Inspirations

The towns wink at isekai and fantasy works we love, including *Konosuba*, *Spice & Wolf*, *Amagi Brilliant Park*,
*Combatants Will Be Dispatched!*, *Lazy Dungeon Master*, *Kamikatsu*, *Fate/Grand Order*, *Gintama*, *Surviving the
Game as a Barbarian* and *Isekai Quartet*. All names, texts and art in this game are our own. We use no characters,
quotes or official art from these works, and this project is not affiliated with their authors or publishers.

Ideas for the AI metrics were inspired by public experiments with language models playing board games.

## License

© 2026 chevreOtaku.

- **Code**: [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).
- **Art and texts** (cards, names, rules): [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
- **Content creators welcome.** You may stream the game and make videos of it, **monetized or not**. That is
  explicitly allowed, despite the non-commercial terms above (see [CONTENT_CREATORS.md](CONTENT_CREATORS.md)).

The full rules fit on one page: [RULES.md](RULES.md).
- **Commercial use** (selling or distributing the game, using it in a paid product) needs the author's permission.
  Ask by opening an issue.
- **The name "Traveler Quartet" is not licensed.** If you fork the project, please give your version another name.

Because of the non-commercial terms, this project is **source-available**, not "open source" in the OSI sense.
