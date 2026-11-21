"""What happened since a player's last DECISION (plan step 7, P-TQ20): the public events, in sentences, capped --
the material an AI player can judge. Bounded by its last decision, not its last turn (it answers auctions and offers
out of turn). The same filter as the server's log: a rival's kept card stays "a kept card"."""

from factory import game
from traveler_quartet.players.command_player import CommandPlayer
from traveler_quartet.players.recent import summary_lines
from traveler_quartet.rules.state import Event

NAMES = [sq.name for sq in game().board.squares]


def _ev(kind, player, **data):
    return (1, Event(kind, player, tuple(data.items())))


def _lines(events, viewer=0, cap=30):
    return summary_lines(events, game().catalog, NAMES, viewer, cap)


def test_common_events_read_as_sentences_with_names_and_amounts():
    text = "\n".join(_lines([_ev("bought", 1, square=6, price=50, bank=-50), _ev("rent_paid", 0, to=1, amount=7),
                             _ev("said", 2, action="roll", text="good luck"), _ev("trade_refused", 2, **{"from": 0})]))
    assert f"player 1 bought [6] {NAMES[6]} for 50" in text and "you paid 7 rent to player 1" in text
    assert 'player 2 said: "good luck"' in text and "player 2 refused your offer" in text and "bank" not in text


def test_a_rivals_kept_card_stays_secret_but_mine_is_named():
    lines = _lines([_ev("card", 1, card="mirror"), _ev("card", 0, card="rope")])
    assert "mirror" not in "\n".join(lines) and "a kept card" in lines[0] and "rope" in lines[1]


def test_the_summary_is_capped_and_says_how_much_was_left_out():
    lines = _lines([_ev("rolled", 1, dice=(1, 2))] * 40, cap=30)
    assert len(lines) == 31 and "10 earlier events not shown" in lines[0]


def test_an_unknown_event_still_reads_without_crashing():
    line = _lines([_ev("something_new", 3, amount=5, bank=-5)])[0]
    assert "player 3" in line and "amount=5" in line and "bank" not in line


def _player(history):
    prompts = []

    def ask(prompt):
        prompts.append(prompt)
        return '{"action": "roll", "message": ""}'
    return CommandPlayer(ask, seat=0, history=lambda: history), prompts


def test_the_ai_reads_only_what_happened_since_its_last_decision():
    history = [_ev("bought", 1, square=6, price=50)]
    player, prompts = _player(history)
    state = game()
    player(state, ("roll", "build:1"))
    history.append(_ev("bought", 1, square=8, price=50))
    player(state, ("roll", "build:1"))
    assert NAMES[6] in prompts[0] and "Since your last decision" in prompts[0]
    assert NAMES[8] in prompts[1] and f"[6] {NAMES[6]} for" not in prompts[1]


def test_an_automatic_move_does_not_move_its_cursor():
    history = [_ev("bought", 1, square=6, price=50)]
    player, prompts = _player(history)
    state = game()
    player.negotiable = lambda s: False
    assert player(state, ("roll",)) == ("roll", None) and prompts == []
    player(state, ("roll", "build:1"))
    assert NAMES[6] in prompts[-1]


def test_the_journal_keeps_the_size_of_the_prompt_and_of_the_summary():
    player, _ = _player([_ev("bought", 1, square=6, price=50)])
    player(game(), ("roll", "build:1"))
    note = player.log[-1]
    assert note["prompt_chars"] > note["summary_chars"] > 0


def test_without_a_history_there_is_no_summary_section():
    prompts = []
    player = CommandPlayer(lambda p: prompts.append(p) or '{"action": "roll"}', seat=0)
    player(game(), ("roll", "build:1"))
    assert "Since your last decision" not in prompts[0] and player.log[-1]["summary_chars"] == 0


def test_every_event_the_engine_can_write_reads_as_a_sentence_not_as_raw_fields():
    """A guard (21/11, chevre: QoL for the AIs): any `Event("<kind>"` written in the rules has its sentence -- a new
    kind without one fails here instead of reaching the players as `debt_opened (to=1, amount=680)`."""
    import re
    from pathlib import Path
    from traveler_quartet.players.recent import _sentences
    rules = Path(__file__).resolve().parents[1] / "src" / "traveler_quartet" / "rules"
    kinds = {k for f in rules.glob("*.py") for k in re.findall(r'Event\("([a-z_]+)"', f.read_text(encoding="utf-8"))}
    assert len(kinds) > 30 and not kinds - set(_sentences(NAMES, str)), sorted(kinds - set(_sentences(NAMES, str)))


def test_the_new_sentences_name_squares_players_and_amounts():
    text = "\n".join(_lines([
        _ev("debt_opened", 1, to=2, amount=680), _ev("debt_opened", 1, to="bank", amount=50),
        _ev("debt_paid", 1, to=2, amount=680), _ev("sold", 1, square=3, level=1, bank=15),
        _ev("unmortgaged", 1, square=11, bank=-77), _ev("cursed", 1, target=0), _ev("mirrored", 0, back_to=1),
        _ev("left_dungeon", 1, paid=50, bank=-50), _ev("left_dungeon", 1, by="double"),
        _ev("stall_requested", 1, square=6, owner=0), _ev("stall_shared", 0, square=6, partner=1, bank=-20),
        _ev("stayed_in_dungeon", 1, left=2), _ev("disaster", 1, town="brown", destroyed=2)]))
    assert "player 1 owes 680 to player 2 and is in debt" in text and "owes 50 to the bank" in text
    assert "player 1 paid the debt of 680 to player 2" in text
    assert f"player 1 sold a building on [3] {NAMES[3]} (now level 1)" in text
    assert f"player 1 lifted the mortgage on [11] {NAMES[11]}" in text
    assert "player 1 cursed you" in text and "you sent the curse back to player 1 with the mirror" in text
    assert "player 1 paid 50 to leave the dungeon" in text and "player 1 left the dungeon with a double" in text
    assert f"player 1 asked you to share a stall on [6] {NAMES[6]}" in text
    assert f"you shared a stall on [6] {NAMES[6]} with player 1" in text
    assert "player 1 stayed in the dungeon (2 turns left)" in text and "2 buildings destroyed in brown" in text
    assert "=" not in text


def test_a_card_drawn_in_public_is_read_with_what_it_does_a_rivals_kept_card_still_without():
    catalog = game().catalog
    lines = _lines([_ev("card", 1, card="birthday"), _ev("card", 1, card="mirror")])
    assert lines[0].endswith(f"player 1 drew the card birthday: {catalog['birthday']['text']}")
    assert lines[1].endswith("player 1 drew a kept card") and "mirror" not in lines[1]
