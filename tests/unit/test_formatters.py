from datetime import datetime, timezone

from services.formatters import (
    format_previous_comment,
    format_previous_exercise_result,
    select_latest_comment,
    truncate_comment,
)


def test_truncate_comment() -> None:
    assert truncate_comment(None) == "Без комментариев"
    assert truncate_comment("short") == "short"
    long_text = "x" * 60
    assert len(truncate_comment(long_text)) == 50


def test_format_previous_comment() -> None:
    text = format_previous_comment(
        {"comment": "test", "date": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    )
    assert "test" in text
    assert "01.01.2026" in text


def test_select_latest_comment() -> None:
    latest = select_latest_comment(
        [
            {"comment": "old", "date": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"comment": "new", "date": datetime(2026, 2, 1, tzinfo=timezone.utc)},
        ]
    )
    assert latest is not None
    assert latest["comment"] == "new"


def test_format_previous_exercise_result() -> None:
    text = format_previous_exercise_result(
        {
            "date": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "sets": [
                {"set_number": 1, "weight": 100.0, "reps": 10},
                {"set_number": 2, "weight": 105.0, "reps": 8},
            ],
            "comment": "Техника стала лучше",
        }
    )
    assert "Предыдущий результат (01.03.2026)" in text
    assert "Подход 1: 100.0 кг × 10" in text
    assert "Подход 2: 105.0 кг × 8" in text
    assert "Техника стала лучше" in text
