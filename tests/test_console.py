"""Playing in the CONSOLE (step 7): a human plays against computer players through a game session -- he sees only his
view, chooses among numbered legal actions, may add a message, and builds a trade without typing its format. The
keyboard is replaced here by scripted answers."""

from traveler_quartet.match.console import build_offer, parse_choice, play_console


def _scripted(*answers, then="1"):
    queue = list(answers)
    return lambda prompt="": queue.pop(0) if queue else then


def _quiet():
    lines = []
    return lines, lambda text="": lines.append(str(text))


def test_a_number_picks_a_legal_action_and_the_rest_is_the_message():
    legal = ("roll", "build:1", "build:3")
    assert parse_choice("2", legal) == ("build:1", None)
    assert parse_choice("1 good luck all", legal) == ("roll", "good luck all")


def test_anything_else_is_not_a_choice():
    legal = ("roll", "pass")
    assert parse_choice("3", legal) is None and parse_choice("0", legal) is None
    assert parse_choice("roll", legal) is None and parse_choice("", legal) is None


def test_an_offer_is_built_from_simple_answers():
    assert build_offer(1, 40, [], [], 0, [3, 5], ["mirror"]) == "offer:1:40:::0:3,5:mirror"
    assert build_offer(2, 0, [6], ["rope"], 25, [], []) == "offer:2:0:6:rope:25::"


def test_a_whole_short_game_is_played_and_ends_with_the_ranking():
    lines, write = _quiet()
    result = play_console(("normal", "normal"), seed=1, rounds=2, read=_scripted(), write=write)
    assert result["over"] is True and "Final ranking" in "\n".join(lines)


def test_a_wrong_answer_is_asked_again_and_never_crashes():
    lines, write = _quiet()
    play_console(("easy",), seed=1, rounds=1, read=_scripted("banana", "99"), write=write)
    assert sum("not a choice" in line for line in lines) >= 2


def test_the_player_sees_only_his_view_never_the_seed_or_the_decks():
    lines, write = _quiet()
    play_console(("normal",), seed=1, rounds=1, read=_scripted(), write=write)
    text = "\n".join(lines)
    assert "seed" not in text.lower() and "decks" not in text.lower()


def test_typing_q_leaves_the_game():
    lines, write = _quiet()
    result = play_console(("normal",), seed=1, rounds=5, read=_scripted("q"), write=write)
    assert result["over"] is False and result["left"] is True


def test_a_message_reaches_the_table_log():
    lines, write = _quiet()
    play_console(("normal",), seed=1, rounds=1, read=_scripted("1 hello table"), write=write)
    assert any("hello table" in line for line in lines)


def test_the_command_knows_the_cli_mode_and_its_opponents():
    from traveler_quartet.__main__ import build_parser
    args = build_parser().parse_args(["cli", "--opponents", "hard,easy", "--seed", "7"])
    assert args.mode == "cli" and args.opponents == "hard,easy" and args.seed == 7


def test_an_offer_typed_with_o_reaches_the_engine():
    lines, write = _quiet()
    play_console(("normal",), seed=1, rounds=1, read=_scripted("o", "1", "10", "", "", "0", "", ""), write=write)
    assert any("refused by the engine" in line and "offer:1:10" in line for line in lines)
