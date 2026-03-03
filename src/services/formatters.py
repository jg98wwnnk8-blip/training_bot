from __future__ import annotations

from datetime import datetime


def truncate_comment(comment: str | None, max_length: int = 50) -> str:
    if not comment:
        return "Без комментариев"
    if len(comment) <= max_length:
        return comment
    return comment[: max_length - 3] + "..."


def format_previous_comment(comment_data: dict | None) -> str:
    if not comment_data:
        return ""
    comment = str(comment_data["comment"])
    date_val = comment_data["date"]
    if isinstance(date_val, datetime):
        date_str = date_val.strftime("%d.%m.%Y")
    else:
        date_str = str(date_val)
    return f"💬 Прошлый комментарий:\n«{comment}»\n({date_str})"


def format_workout_overview(title: str, items: list[dict]) -> str:
    lines = [f"📅 {title} (в процессе)", "────────────────"]
    if not items:
        lines.append("Пока нет упражнений")
        return "\n".join(lines)

    for idx, item in enumerate(items, 1):
        sets_preview = ", ".join(str(s["reps"]) for s in item["sets"])
        weight = item["sets"][0]["weight"] if item["sets"] else 0
        lines.append(f"{idx}️⃣ {item['exercise_name_snapshot']}")
        if item["sets"]:
            lines.append(f"   • {weight} кг × {sets_preview}")
        lines.append(f"   💬 {item['comment'] or 'Без комментариев'}")
    return "\n".join(lines)


def select_latest_comment(records: list[dict]) -> dict | None:
    if not records:
        return None
    return sorted(records, key=lambda r: r["date"], reverse=True)[0]


def format_previous_exercise_result(result_data: dict | None) -> str:
    if not result_data:
        return ""

    date_val = result_data.get("date")
    if isinstance(date_val, datetime):
        date_str = date_val.strftime("%d.%m.%Y")
    else:
        date_str = "неизвестно"

    sets = result_data.get("sets", [])
    lines = [f"📌 Предыдущий результат ({date_str}):"]
    for s in sets:
        lines.append(f"• Подход {s['set_number']}: {s['weight']} кг × {s['reps']}")

    comment = (result_data.get("comment") or "").strip()
    if comment:
        lines.append(f"💬 Комментарий: {comment}")

    return "\n".join(lines)
