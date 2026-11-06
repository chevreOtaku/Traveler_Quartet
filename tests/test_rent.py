from dataclasses import replace

from factory import MECHANICS_RENT_PERCENT
from traveler_quartet.rules.board import load_board
from traveler_quartet.rules.economy import load_economy, rent

BOARD = load_board()
ECONOMY = replace(load_economy(), rent_percent=MECHANICS_RENT_PERCENT)
NOBODY = (None,) * 40


def _owned(**owners):
    table = list(NOBODY)
    for index, player in owners.items():
        table[int(index[1:])] = player
    return tuple(table)


def test_an_unowned_district_costs_nothing():
    assert rent(BOARD, ECONOMY, NOBODY, 37) == 0


def test_a_bare_district_costs_ten_percent_of_its_price():
    assert rent(BOARD, ECONOMY, _owned(s37=0), 37) == 17


def test_owning_the_whole_town_doubles_the_rent():
    assert rent(BOARD, ECONOMY, _owned(s37=0, s39=0), 37) == 34


def test_two_owners_in_one_town_do_not_double():
    assert rent(BOARD, ECONOMY, _owned(s37=0, s39=1), 37) == 17
