from __future__ import annotations

from sqlalchemy import Select, and_, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Exercise, MuscleGroup, Workout, WorkoutExercise, WorkoutStatus


async def get_muscle_groups_for_user(session: AsyncSession, user_id: int) -> list[MuscleGroup]:
    stmt: Select[tuple[MuscleGroup]] = (
        select(MuscleGroup)
        .where(or_(MuscleGroup.user_id.is_(None), MuscleGroup.user_id == user_id))
        .order_by(MuscleGroup.sort_order.asc(), MuscleGroup.name.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_custom_muscle_group(
    session: AsyncSession, user_id: int, name: str, emoji: str = "💪"
) -> MuscleGroup:
    group = MuscleGroup(user_id=user_id, name=name, emoji=emoji, is_custom=True)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


async def rename_custom_muscle_group(
    session: AsyncSession, user_id: int, group_id: int, new_name: str
) -> bool:
    result = await session.execute(
        update(MuscleGroup)
        .where(
            MuscleGroup.id == group_id,
            MuscleGroup.user_id == user_id,
            MuscleGroup.is_custom.is_(True),
        )
        .values(name=new_name)
    )
    await session.commit()
    return result.rowcount > 0


async def delete_custom_muscle_group(session: AsyncSession, user_id: int, group_id: int) -> bool:
    group = await session.get(MuscleGroup, group_id)
    if group is None or group.user_id != user_id or not group.is_custom:
        return False
    await session.delete(group)
    await session.commit()
    return True


async def get_exercises_by_group_with_comment_flag(
    session: AsyncSession,
    user_id: int,
    muscle_group_id: int,
) -> list[dict]:
    stmt = (
        select(
            Exercise.id,
            Exercise.name,
            Exercise.is_custom,
            exists(
                select(WorkoutExercise.id)
                .join(Workout, Workout.id == WorkoutExercise.workout_id)
                .where(
                    WorkoutExercise.exercise_id == Exercise.id,
                    Workout.user_id == user_id,
                    Workout.status == WorkoutStatus.COMPLETED.value,
                    WorkoutExercise.comment.is_not(None),
                    WorkoutExercise.comment != "",
                )
            ).label("has_comment"),
        )
        .where(
            and_(
                Exercise.muscle_group_id == muscle_group_id,
                or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
            )
        )
        .order_by(Exercise.name.asc())
    )
    result = await session.execute(stmt)
    return [
        {"id": row[0], "name": row[1], "is_custom": row[2], "has_comment": row[3]}
        for row in result.all()
    ]


async def create_custom_exercise(
    session: AsyncSession, user_id: int, muscle_group_id: int, name: str
) -> Exercise:
    exercise = Exercise(
        user_id=user_id,
        muscle_group_id=muscle_group_id,
        name=name,
        is_custom=True,
    )
    session.add(exercise)
    await session.commit()
    await session.refresh(exercise)
    return exercise


async def rename_custom_exercise(
    session: AsyncSession, user_id: int, exercise_id: int, new_name: str
) -> bool:
    result = await session.execute(
        update(Exercise)
        .where(
            Exercise.id == exercise_id,
            Exercise.user_id == user_id,
            Exercise.is_custom.is_(True),
        )
        .values(name=new_name)
    )
    await session.commit()
    return result.rowcount > 0


async def delete_custom_exercise(session: AsyncSession, user_id: int, exercise_id: int) -> bool:
    exercise = await session.get(Exercise, exercise_id)
    if exercise is None or exercise.user_id != user_id or not exercise.is_custom:
        return False
    await session.delete(exercise)
    await session.commit()
    return True


async def get_custom_muscle_groups(session: AsyncSession, user_id: int) -> list[MuscleGroup]:
    result = await session.execute(
        select(MuscleGroup)
        .where(MuscleGroup.user_id == user_id, MuscleGroup.is_custom.is_(True))
        .order_by(MuscleGroup.created_at.desc())
    )
    return list(result.scalars().all())


async def get_custom_exercises(session: AsyncSession, user_id: int) -> list[Exercise]:
    result = await session.execute(
        select(Exercise)
        .where(Exercise.user_id == user_id, Exercise.is_custom.is_(True))
        .order_by(Exercise.created_at.desc())
    )
    return list(result.scalars().all())


async def get_custom_exercises_by_group(
    session: AsyncSession, user_id: int, muscle_group_id: int
) -> list[Exercise]:
    result = await session.execute(
        select(Exercise)
        .where(
            Exercise.user_id == user_id,
            Exercise.is_custom.is_(True),
            Exercise.muscle_group_id == muscle_group_id,
        )
        .order_by(Exercise.created_at.desc())
    )
    return list(result.scalars().all())
