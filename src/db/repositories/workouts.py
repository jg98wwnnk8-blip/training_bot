from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, delete, func, select, update
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
