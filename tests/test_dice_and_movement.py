from traveler_quartet.rules.dice import roll
from traveler_quartet.rules.movement import advance


def test_a_roll_is_fixed_by_its_seed_and_its_number():
    assert roll(seed=7, number=3) == roll(seed=7, number=3)


def test_dice_stay_between_one_and_six_and_vary():
    rolls = [roll(seed=1, number=n) for n in range(500)]
    faces = {face for pair in rolls for face in pair}
    assert faces == {1, 2, 3, 4, 5, 6}


def test_two_seeds_give_two_sequences():
    first = [roll(seed=1, number=n) for n in range(20)]
    second = [roll(seed=2, number=n) for n in range(20)]
    assert first != second


def test_moving_past_the_last_square_wraps_and_passes_start():
    assert advance(position=38, steps=4, board_size=40) == (2, True)


def test_moving_inside_the_board_does_not_pass_start():
    assert advance(position=5, steps=3, board_size=40) == (8, False)
