from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Exercise, SetEntry, Workout, WorkoutExercise, WorkoutStatus


async def get_in_progress_workout(session: AsyncSession, user_id: int) -> Workout | None:
    result = await session.execute(
        select(Workout)
        .where(Workout.user_id == user_id, Workout.status == WorkoutStatus.IN_PROGRESS.value)
        .order_by(Workout.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_workout(session: AsyncSession, user_id: int, title: str) -> Workout:
    workout = Workout(
        user_id=user_id,
        title=title,
        status=WorkoutStatus.IN_PROGRESS.value,
        date_utc=datetime.now(timezone.utc),
    )
    session.add(workout)
    await session.commit()
    await session.refresh(workout)
    return workout


async def get_or_create_in_progress_workout(session: AsyncSession, user_id: int, title: str) -> Workout:
    current = await get_in_progress_workout(session, user_id)
    if current is not None:
        return current
    return await create_workout(session, user_id, title)


async def complete_workout(session: AsyncSession, user_id: int, workout_id: int, comment: str | None) -> bool:
    result = await session.execute(
        update(Workout)
        .where(
            Workout.id == workout_id,
            Workout.user_id == user_id,
            Workout.status == WorkoutStatus.IN_PROGRESS.value,
        )
        .values(status=WorkoutStatus.COMPLETED.value, comment=comment)
    )
    await session.commit()
    return result.rowcount > 0


async def get_workout_with_items(session: AsyncSession, user_id: int, workout_id: int) -> Workout | None:
    stmt: Select[tuple[Workout]] = (
        select(Workout)
        .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
        .where(Workout.id == workout_id, Workout.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_workout_exercise_with_sets(
    session: AsyncSession,
    user_id: int,
    workout_id: int,
    exercise_id: int,
    exercise_name_snapshot: str,
    sets: list[dict],
    comment: str | None,
) -> WorkoutExercise:
    workout = await session.get(Workout, workout_id)
    if workout is None or workout.user_id != user_id:
        raise ValueError("Workout not found")

    last_order = await session.scalar(
        select(func.max(WorkoutExercise.order)).where(WorkoutExercise.workout_id == workout_id)
    )
    next_order = (last_order or 0) + 1

    item = WorkoutExercise(
        workout_id=workout_id,
        exercise_id=exercise_id,
        exercise_name_snapshot=exercise_name_snapshot,
        order=next_order,
        comment=comment,
    )
    session.add(item)
    await session.flush()

    # Safety net for legacy SQLite states: if FK cascade was disabled earlier,
    # stale sets might remain for reused IDs and break UNIQUE(workout_exercise_id, set_number).
    await session.execute(delete(SetEntry).where(SetEntry.workout_exercise_id == item.id))

    for index, set_data in enumerate(sets, start=1):
        session.add(
            SetEntry(
                workout_exercise_id=item.id,
                set_number=index,
                weight=set_data["weight"],
                reps=set_data["reps"],
            )
        )

    await session.commit()
    await session.refresh(item)
    return item


async def get_workout_item(session: AsyncSession, user_id: int, workout_exercise_id: int) -> WorkoutExercise | None:
    result = await session.execute(
        select(WorkoutExercise)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .options(selectinload(WorkoutExercise.sets))
        .where(WorkoutExercise.id == workout_exercise_id, Workout.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_workout_item_comment(
    session: AsyncSession, user_id: int, workout_exercise_id: int, comment: str | None
) -> bool:
    result = await session.execute(
        update(WorkoutExercise)
        .where(
            WorkoutExercise.id == workout_exercise_id,
            WorkoutExercise.workout.has(Workout.user_id == user_id),
        )
        .values(comment=comment)
    )
    await session.commit()
    return result.rowcount > 0


async def update_set_weight(
    session: AsyncSession, user_id: int, workout_exercise_id: int, set_number: int, weight: float
) -> bool:
    result = await session.execute(
        update(SetEntry)
        .where(
            SetEntry.workout_exercise_id == workout_exercise_id,
            SetEntry.set_number == set_number,
            SetEntry.workout_exercise.has(WorkoutExercise.workout.has(Workout.user_id == user_id)),
        )
        .values(weight=weight)
    )
    await session.commit()
    return result.rowcount > 0


async def update_set_reps(
    session: AsyncSession, user_id: int, workout_exercise_id: int, set_number: int, reps: int
) -> bool:
    result = await session.execute(
        update(SetEntry)
        .where(
            SetEntry.workout_exercise_id == workout_exercise_id,
            SetEntry.set_number == set_number,
            SetEntry.workout_exercise.has(WorkoutExercise.workout.has(Workout.user_id == user_id)),
        )
        .values(reps=reps)
    )
    await session.commit()
    return result.rowcount > 0


async def delete_workout_item(session: AsyncSession, user_id: int, workout_exercise_id: int) -> bool:
    result = await session.execute(
        delete(WorkoutExercise).where(
            WorkoutExercise.id == workout_exercise_id,
            WorkoutExercise.workout.has(Workout.user_id == user_id),
        )
    )
    await session.commit()
    return result.rowcount > 0


async def get_last_exercise_comment(
    session: AsyncSession,
    user_id: int,
    exercise_id: int,
) -> dict | None:
    result = await session.execute(
        select(WorkoutExercise.comment, Workout.date_utc)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .where(
            WorkoutExercise.exercise_id == exercise_id,
            Workout.user_id == user_id,
            Workout.status == WorkoutStatus.COMPLETED.value,
            WorkoutExercise.comment.is_not(None),
            WorkoutExercise.comment != "",
        )
        .order_by(Workout.date_utc.desc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    return {"comment": row[0], "date": row[1]}


async def get_last_exercise_result(
    session: AsyncSession,
    user_id: int,
    exercise_id: int,
) -> dict | None:
    result = await session.execute(
        select(WorkoutExercise)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .options(selectinload(WorkoutExercise.sets))
        .where(
            WorkoutExercise.exercise_id == exercise_id,
            Workout.user_id == user_id,
            Workout.status == WorkoutStatus.COMPLETED.value,
        )
        .order_by(Workout.date_utc.desc())
        .limit(1)
    )
    item = result.scalar_one_or_none()
    if item is None:
        return None

    workout_date = await session.scalar(
        select(Workout.date_utc).where(Workout.id == item.workout_id).limit(1)
    )
    sets = sorted(item.sets, key=lambda s: s.set_number)
    return {
        "date": workout_date,
        "comment": item.comment,
        "sets": [{"set_number": s.set_number, "weight": s.weight, "reps": s.reps} for s in sets],
    }


def _workout_aggregates_subquery():
    return (
        select(
            WorkoutExercise.workout_id.label("workout_id"),
            func.count(func.distinct(WorkoutExercise.id)).label("exercise_count"),
            func.coalesce(func.sum(SetEntry.weight * SetEntry.reps), 0.0).label("total_volume"),
        )
        .select_from(WorkoutExercise)
        .outerjoin(SetEntry, SetEntry.workout_exercise_id == WorkoutExercise.id)
        .group_by(WorkoutExercise.workout_id)
        .subquery()
    )


async def list_completed_workouts(
    session: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    aggregates = _workout_aggregates_subquery()
    total_stmt = select(func.count(Workout.id)).where(
        Workout.user_id == user_id,
        Workout.status == WorkoutStatus.COMPLETED.value,
    )
    total = int(await session.scalar(total_stmt) or 0)

    rows = await session.execute(
        select(
            Workout.id,
            Workout.title,
            Workout.date_utc,
            Workout.comment,
            func.coalesce(aggregates.c.exercise_count, 0),
            func.coalesce(aggregates.c.total_volume, 0.0),
        )
        .outerjoin(aggregates, aggregates.c.workout_id == Workout.id)
        .where(Workout.user_id == user_id, Workout.status == WorkoutStatus.COMPLETED.value)
        .order_by(Workout.date_utc.desc())
        .limit(limit)
        .offset(offset)
    )

    items = [
        {
            "id": row[0],
            "title": row[1],
            "date_utc": row[2].isoformat() if row[2] else "",
            "comment": row[3],
            "exercise_count": int(row[4] or 0),
            "total_volume": float(row[5] or 0.0),
        }
        for row in rows.all()
    ]
    return items, total


async def get_workout_detail_payload(
    session: AsyncSession, user_id: int, workout_id: int
) -> dict | None:
    workout = await get_workout_with_items(session, user_id, workout_id)
    if workout is None:
        return None

    exercises = []
    for item in sorted(workout.exercises, key=lambda x: x.order):
        item_sets = sorted(item.sets, key=lambda s: s.set_number)
        exercises.append(
            {
                "workout_exercise_id": item.id,
                "exercise_id": item.exercise_id,
                "exercise_name": item.exercise_name_snapshot,
                "comment": item.comment,
                "sets": [
                    {"set_number": s.set_number, "weight": s.weight, "reps": s.reps}
                    for s in item_sets
                ],
            }
        )

    return {
        "id": workout.id,
        "title": workout.title,
        "date_utc": workout.date_utc.isoformat(),
        "comment": workout.comment,
        "status": workout.status,
        "exercises": exercises,
    }


async def search_completed_workouts(
    session: AsyncSession,
    user_id: int,
    muscle_group_id: int | None = None,
    exercise_id: int | None = None,
    date_from: datetime | None = None,
) -> tuple[list[dict], int]:
    aggregates = _workout_aggregates_subquery()

    conditions = [
        Workout.user_id == user_id,
        Workout.status == WorkoutStatus.COMPLETED.value,
    ]
    if date_from is not None:
        conditions.append(Workout.date_utc >= date_from)

    if muscle_group_id is not None:
        conditions.append(
            Workout.exercises.any(
                WorkoutExercise.exercise_id.in_(
                    select(Exercise.id).where(Exercise.muscle_group_id == muscle_group_id)
                )
            )
        )
    if exercise_id is not None:
        conditions.append(Workout.exercises.any(WorkoutExercise.exercise_id == exercise_id))

    base = select(Workout.id).where(and_(*conditions)).subquery()

    total_stmt = select(func.count()).select_from(base)
    total = int(await session.scalar(total_stmt) or 0)

    rows = await session.execute(
        select(
            Workout.id,
            Workout.title,
            Workout.date_utc,
            Workout.comment,
            func.coalesce(aggregates.c.exercise_count, 0),
            func.coalesce(aggregates.c.total_volume, 0.0),
        )
        .outerjoin(aggregates, aggregates.c.workout_id == Workout.id)
        .where(Workout.id.in_(select(base.c.id)))
        .order_by(Workout.date_utc.desc())
    )

    items = [
        {
            "id": row[0],
            "title": row[1],
            "date_utc": row[2].isoformat() if row[2] else "",
            "comment": row[3],
            "exercise_count": int(row[4] or 0),
            "total_volume": float(row[5] or 0.0),
        }
        for row in rows.all()
    ]
    return items, total
