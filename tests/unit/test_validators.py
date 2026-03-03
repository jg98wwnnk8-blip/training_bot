from services.validators import is_valid_number, is_valid_reps, is_valid_weight, parse_number


def test_number_parsing() -> None:
    assert is_valid_number("100")
    assert is_valid_number("100.5")
    assert is_valid_number("100,5")
    assert parse_number("100,5") == 100.5
    assert not is_valid_number("abc")


def test_weight_range() -> None:
    assert is_valid_weight("0.5")
    assert is_valid_weight("500")
    assert not is_valid_weight("0.1")
    assert not is_valid_weight("700")


def test_reps_range() -> None:
    assert is_valid_reps("1")
    assert is_valid_reps("200")
    assert not is_valid_reps("0")
    assert not is_valid_reps("201")
