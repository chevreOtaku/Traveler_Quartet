from collections import Counter

from traveler_quartet.rules.board import load_board


def test_the_board_has_40_squares_and_22_districts():
    board = load_board()
    assert len(board.squares) == 40
    assert sum(1 for s in board.squares if s.kind == "district") == 22


def test_the_eight_towns_have_the_classic_sizes():
    sizes = {town: len(indices) for town, indices in load_board().towns.items()}
    assert sizes == {
        "brown": 2, "light_blue": 3, "purple": 3, "orange": 3,
        "red": 3, "yellow": 3, "green": 3, "dark_blue": 2,
    }


def test_the_special_squares_are_counted_as_designed():
    kinds = Counter(s.kind for s in load_board().squares)
    assert kinds["chance"] == 3
    assert kinds["event"] == 2
    assert kinds["tax"] == 3
    assert kinds["portal"] == 4
    assert kinds["utility"] == 2
    assert load_board().squares[0].kind == "start"


def test_prices_are_the_starting_scale():
    squares = load_board().squares
    assert squares[1].price == 30
    assert squares[39].price == 200
