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
