"""The state as TEXT (step 7), in Markdown -- what a human reads in the console and what an AI player reads at each
decision. Built ONLY from `view(state, player)`: it cannot show a secret that the view hides. It uses the PUBLIC facts
of the view (D47) -- the order of the round, a double, net worths, rents, towns, the rules -- and stays short: an AI
player reads it at every move."""

from typing import Dict, List, Sequence

QUESTIONS = {
    "roll": "Start of your turn: roll the dice, or act first (build, trade, play a card).",
    "buy": "You landed on a free district: buy it, or pass (it then goes to auction).",
    "auction": "An auction is open: raise the bid, or drop out for good.",
    "sealed": "The bank sells a district by sealed bids: write ONE secret bid.",
    "trade": "An offer is waiting for your answer: accept, refuse or counter.",
    "stall_request": "A rival asks to share a stall on your district: accept or refuse.",
    "jump": "You are on a portal: jump to the next portal, or stay.",
    "target": "Choose the player your curse is played on.",
    "debt": "You owe more than you have: sell houses or mortgage a district, or go bankrupt.",
}
CONTRACT = ("To offer a trade, write `offer:<player>:<give_gold>:<give_squares>:<give_cards>:<ask_gold>:<ask_squares>:"
            "<ask_cards>` (squares by number, comma-separated; an empty field = nothing). A counter-offer: "
            "`counter:<give_gold>:<give_squares>:<give_cards>:<ask_gold>:<ask_squares>:<ask_cards>`. What each side "
            "receives must be worth between half and double what it gives.")
CONTRACT_NAMED = ('To offer a trade, answer {"action": "offer", "to": <player>, "give": {"gold": <amount>, "squares": '
                  '[<square numbers>], "cards": [<card ids>]}, "ask": {"gold": <amount>, "squares": [<square numbers>], '
                  '"cards": [<card ids>]}, "message": "..."} (leave out what is empty). A counter-offer: the same without '
                  '"to", with "action": "counter". What each side receives must be worth between half and double what '
                  "it gives.")
FIELDS = "<give_gold>:<give_squares>:<give_cards>:<ask_gold>:<ask_squares>:<ask_cards>"
# How an AI seat sees an open negotiation: `fields` = the contract explained under the choices (the default) ;
# `named` = the same place, written with named fields ; `listed` = the same syntax, each open offer IN the choices.
OFFER_STYLES = ("fields", "named", "listed")
Seen = Dict[str, object]


def _who(seen: Seen, seat) -> str:
    return "you" if seat == seen["me"]["seat"] else f"player {seat}"


def _square_line(sq: Dict[str, object]) -> str:
    extra = [f"town {sq['town']}"] if sq["town"] else []
    extra += [f"{sq['buildings']} building(s)"] if sq["buildings"] else []
    extra += ["mortgaged"] if sq["mortgaged"] else []
    extra += [f"rent {sq['rent']}"] if sq.get("rent") else []
    extra += [f"rent dice x {sq['rent_per_dice_point']}"] if sq.get("rent_per_dice_point") else []
    return f"- [{sq['index']}] {sq['name']} ({', '.join([sq['kind']] + extra)})"


def _others(seen: Seen) -> List[str]:
    lines = []
    for o in seen["others"]:
        state = "out" if o["out"] else ("in the dungeon" if o["in_dungeon"] else f"on square {o['position']}")
        cards = f", {o['cards_held']} kept card{'s' if o['cards_held'] != 1 else ''}" if o["cards_held"] else ""
        lines.append(f"- Player {o['seat']}: {o['cash']} gold (net worth {o['net_worth']}), {state}{cards}")
    return lines


def _owned(seen: Seen, seat: int) -> List[str]:
    return [_square_line(sq) for sq in seen["board"] if sq["owner"] == seat]


def _towns(seen: Seen) -> List[str]:
    towns: Dict[str, List[str]] = {}
    for sq in seen["board"]:
        if sq["town"]:
            holder = f"free {sq['price']}" if sq["owner"] is None else _who(seen, sq["owner"])
            towns.setdefault(sq["town"], []).append(f"[{sq['index']}] {holder}")
    return ["", "## Towns (a whole town doubles its rents and allows houses)"] + [
        f"- {town}: {', '.join(parts)}" for town, parts in towns.items()]


def _rules(seen: Seen) -> str:
    r = seen["rules"]
    levels = " / ".join(f"x{m}" for m in r["rent_multipliers_by_level"][1:])
    return (f"Rules: rent = {r['rent_percent']} % of the price, x{r['rent_multiplier_whole_town']} for a whole town, "
            f"{levels} with 1-{len(r['rent_multipliers_by_level']) - 1} buildings; +{r['salary']} at Start; the final "
            f"score counts cash + districts + buildings at {r['final_value_percent']} %.")


def _items(seen: Seen, gold: int, squares: Sequence[int], cards: Sequence[str]) -> str:
    parts = [f"{gold} gold"] if gold else []
    parts += [f"[{i}] {seen['board'][i]['name']}" for i in squares] + [f"card {c}" for c in cards]
    return ", ".join(parts) or "nothing"


def _offer(seen: Seen) -> str:
    t, terms = seen["trade"], seen["trade"]["terms"]
    give = _items(seen, terms["give_gold"], terms["give_squares"], terms["give_cards"])
    ask = _items(seen, terms["ask_gold"], terms["ask_squares"], terms["ask_cards"])
    return f"Player {t['proposer']} offers {_who(seen, t['responder'])} {give} in exchange for {ask}."


def _to_buy(seen: Seen) -> List[str]:
    sq = seen["board"][seen["me"]["position"]]
    if seen["pending"] != "buy" or not seen["your_turn"] or not sq["town"]:
        return []
    town = [s for s in seen["board"] if s["town"] == sq["town"]]
    mine = sum(1 for s in town if s["owner"] == seen["me"]["seat"])
    return ["", f"[{sq['index']}] {sq['name']}: price {sq['price']} -- you own {mine} of {len(town)} in {sq['town']}."]


def _listed(name: str) -> str:
    if name == "counter":
        return f"- `counter:{FIELDS}` -- a counter-offer"
    return f"- `{name}:{FIELDS}` -- a trade with player {name.split(':')[1]}"


def _named_open(names: Sequence[str]) -> str:
    rivals = [n.split(":")[1] for n in names if n.startswith("offer:")]
    parts = ([f"`offer` to player {', '.join(rivals)}"] if rivals else []) + (["`counter`"] if "counter" in names else [])
    return "Open now: " + ", ".join(parts)


def _negotiation(names: Sequence[str], style: str) -> List[str]:
    if not any(n.startswith("offer:") or n == "counter" for n in names):
        return []
    if style == "listed":
        return [_listed(n) for n in names] + ["", CONTRACT]
    if style == "named":
        return ["", CONTRACT_NAMED, _named_open(names)]
    return ["", CONTRACT, "Open now: " + ", ".join(f"`{n}`" for n in names)]


def _question(seen: Seen) -> str:
    if seen["pending"] == "talk":
        return f"Player {seen['talk']['speaker']} speaks to you: answer them in your message"
    return QUESTIONS.get(seen["pending"], seen["pending"])


def _choices(seen: Seen, style: str) -> List[str]:
    if not seen["your_turn"]:
        return []
    names = seen["negotiations"]
    lines = ["", "## Your choices", f"{_question(seen)} (question: `{seen['pending']}`)", ""]
    lines += [f"- `{a}`" for a in seen["legal_actions"]]
    lines += [f"- `{n}` -- speak to player {n.split(':')[1]}; they answer before you go on"
              for n in names if n.startswith("talk:")]
    return lines + _negotiation([n for n in names if not n.startswith("talk:") and n != "reply"], style)


def _header(seen: Seen) -> List[str]:
    me = seen["me"]
    here = str(seen["board"][me["position"]]["name"]).rstrip(".")
    lines = [f"# Round {seen['round']} / {seen['rounds']} -- you are player {me['seat']}",
             "Order this round: " + ", ".join(_who(seen, s) for s in seen["order"]), "",
             f"You have {me['cash']} gold (net worth {me['net_worth']}) and stand on [{me['position']}] {here}."
             + (" You are in the dungeon." if me["in_dungeon"] else "")]
    if seen["doubles"] and seen["current"] == me["seat"] and seen["your_turn"]:
        lines.append("You rolled a double: you play again.")
    if me["cards"]:
        effects = {c["id"]: c["text"] for c in seen["cards"]}
        lines.append("Your kept cards (secret): " + "; ".join(f"{c} ({effects.get(c, '')})" for c in me["cards"]))
    return lines


def render(seen: Seen, offer_style: str = "fields") -> str:
    """`offer_style`: how an open negotiation is shown (OFFER_STYLES) -- the rest of the text never changes."""
    if offer_style not in OFFER_STYLES:
        raise ValueError(f"unknown offer style {offer_style!r}; known: {', '.join(OFFER_STYLES)}")
    me = seen["me"]
    lines = _header(seen) + [_rules(seen)]
    lines += ["", "## Yours"] + (_owned(seen, me["seat"]) or ["- nothing yet"])
    lines += ["", "## The others"] + _others(seen)
    for o in seen["others"]:
        lines += [f"### Player {o['seat']} owns"] + (_owned(seen, o["seat"]) or ["- nothing"])
    lines += _towns(seen)
    if "auction" in seen:
        a = seen["auction"]
        leader = "nobody yet" if a["leader"] is None else _who(seen, a["leader"])
        lines += ["", f"Auction on [{a['square']}] {seen['board'][a['square']]['name']} (price {seen['board'][a['square']]['price']}): {a['price']} gold, leader {leader}"]
    if "trade" in seen:
        lines += ["", _offer(seen)]
    if "debt" in seen:
        lines += ["", f"You owe {seen['debt']} gold."]
    return "\n".join(lines + _to_buy(seen) + _choices(seen, offer_style))
