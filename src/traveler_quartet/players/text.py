"""The state as TEXT (step 7), in Markdown -- what a human reads in the console and what an AI player reads at each
decision. Built ONLY from `view(state, player)`: it cannot show a secret that the view hides."""

from typing import Dict, List

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


def _square_line(sq: Dict[str, object]) -> str:
    extra = [f"town {sq['town']}"] if sq["town"] else []
    extra += [f"{sq['buildings']} building(s)"] if sq["buildings"] else []
    extra += ["mortgaged"] if sq["mortgaged"] else []
    return f"- [{sq['index']}] {sq['name']} ({', '.join([sq['kind']] + extra)})"


def _others(seen: Dict[str, object]) -> List[str]:
    lines = []
    for o in seen["others"]:
        state = "out" if o["out"] else ("in the dungeon" if o["in_dungeon"] else f"on square {o['position']}")
        cards = f", {o['cards_held']} kept card{'s' if o['cards_held'] != 1 else ''}" if o["cards_held"] else ""
        lines.append(f"- Player {o['seat']}: {o['cash']} gold, {state}{cards}")
    return lines


def _owned(seen: Dict[str, object], seat: int) -> List[str]:
    return [_square_line(sq) for sq in seen["board"] if sq["owner"] == seat]


def _choices(seen: Dict[str, object]) -> List[str]:
    if not seen["your_turn"]:
        return []
    lines = ["", "## Your choices", f"{QUESTIONS.get(seen['pending'], seen['pending'])} (question: `{seen['pending']}`)", ""]
    lines += [f"- `{a}`" for a in seen["legal_actions"]]
    if any(n.startswith("offer:") or n == "counter" for n in seen["negotiations"]):
        lines += ["", CONTRACT, "Open now: " + ", ".join(f"`{n}`" for n in seen["negotiations"])]
    return lines


def render(seen: Dict[str, object]) -> str:
    me = seen["me"]
    here = seen["board"][me["position"]]["name"]
    lines = [f"# Round {seen['round']} / {seen['rounds']} -- you are player {me['seat']}", "",
             f"You have {me['cash']} gold and stand on [{me['position']}] {here}."
             + (" You are in the dungeon." if me["in_dungeon"] else "")]
    if me["cards"]:
        lines.append("Your kept cards (secret): " + ", ".join(me["cards"]))
    lines += ["", "## Yours"] + (_owned(seen, me["seat"]) or ["- nothing yet"])
    lines += ["", "## The others"] + _others(seen)
    for o in seen["others"]:
        lines += [f"### Player {o['seat']} owns"] + (_owned(seen, o["seat"]) or ["- nothing"])
    if "auction" in seen:
        a = seen["auction"]
        lines += ["", f"Auction on square [{a['square']}]: {a['price']} gold, leader player {a['leader']}"]
    if "trade" in seen:
        t = seen["trade"]
        lines += ["", f"Offer from player {t['proposer']} to player {t['responder']}: {t['terms']}"]
    if "debt" in seen:
        lines += ["", f"You owe {seen['debt']} gold."]
    return "\n".join(lines + _choices(seen))
