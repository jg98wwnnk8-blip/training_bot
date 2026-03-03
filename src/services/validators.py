import re


_NUMBER_PATTERN = re.compile(r"^\d+([.,]\d{1,2})?$")


def is_valid_number(text: str) -> bool:
    return bool(_NUMBER_PATTERN.match(text.strip()))


def parse_number(text: str) -> float | None:
    value = text.strip().replace(",", ".")
    if not is_valid_number(value):
        return None
    return float(value)


def is_valid_weight(text: str) -> bool:
    value = parse_number(text)
    return value is not None and 0.5 <= value <= 500


def is_valid_reps(text: str) -> bool:
    if not text.strip().isdigit():
        return False
    reps = int(text.strip())
    return 1 <= reps <= 200
