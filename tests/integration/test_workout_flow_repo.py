from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from db.models import Exercise, MuscleGroup, SetEntry, Workout, WorkoutExercise, WorkoutStatus
from db.repositories.catalog import create_custom_muscle_group
from db.repositories.workouts import (
    add_workout_exercise_with_sets,
    complete_workout,
    create_workout,
    get_last_exercise_comment,
    get_last_exercise_result,
    list_completed_workouts,
    search_completed_workouts,
    get_workout_with_items,
)


@pytest.mark.asyncio
async def test_create_complete_workout(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 100
    session.add_all([
        Workout(id=999, user_id=user_id, title="dummy", status=WorkoutStatus.COMPLETED.value),
    ])
    await session.commit()

    workout = await create_workout(session, user_id=user_id, title="Day 1")
    assert workout.status == WorkoutStatus.IN_PROGRESS.value

    ok = await complete_workout(session, user_id=user_id, workout_id=workout.id, comment="done")
    assert ok

    loaded = await get_workout_with_items(session, user_id=user_id, workout_id=workout.id)
    assert loaded is not None
    assert loaded.status == WorkoutStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_add_exercise_and_sets(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 200
    session.add(MuscleGroup(id=1, name="Грудь", emoji="🔴", sort_order=1, is_custom=False))
    session.add(Exercise(id=1, muscle_group_id=1, name="Жим лёжа", is_custom=False))
    await session.commit()

    workout = await create_workout(session, user_id=user_id, title="Chest")
    item = await add_workout_exercise_with_sets(
        session,
        user_id=user_id,
        workout_id=workout.id,
        exercise_id=1,
        exercise_name_snapshot="Жим лёжа",
        sets=[{"weight": 100.0, "reps": 10}, {"weight": 105.0, "reps": 8}],
        comment="good",
    )
    assert item.id > 0

    loaded = await get_workout_with_items(session, user_id=user_id, workout_id=workout.id)
    assert loaded is not None
    assert len(loaded.exercises) == 1
    assert len(loaded.exercises[0].sets) == 2


@pytest.mark.asyncio
async def test_last_comment_selection(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 300
    session.add(MuscleGroup(id=2, name="Спина", emoji="🔵", sort_order=1, is_custom=False))
    session.add(Exercise(id=2, muscle_group_id=2, name="Тяга", is_custom=False))
    await session.commit()

    w1 = Workout(
        user_id=user_id,
        title="Old",
        status=WorkoutStatus.COMPLETED.value,
        date_utc=datetime.now(timezone.utc) - timedelta(days=10),
    )
    w2 = Workout(
        user_id=user_id,
        title="New",
        status=WorkoutStatus.COMPLETED.value,
        date_utc=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add_all([w1, w2])
    await session.flush()
    session.add_all(
        [
            WorkoutExercise(
                workout_id=w1.id,
                exercise_id=2,
                exercise_name_snapshot="Тяга",
                comment="old comment",
                order=1,
            ),
            WorkoutExercise(
                workout_id=w2.id,
                exercise_id=2,
                exercise_name_snapshot="Тяга",
                comment="new comment",
                order=1,
            ),
        ]
    )
    await session.commit()

    latest = await get_last_exercise_comment(session, user_id=user_id, exercise_id=2)
    assert latest is not None
    assert latest["comment"] == "new comment"


@pytest.mark.asyncio
async def test_custom_group_access_boundaries(session) -> None:  # type: ignore[no-untyped-def]
    owner_id = 400
    other_id = 401

    group = await create_custom_muscle_group(session, user_id=owner_id, name="Предплечья")
    assert group.user_id == owner_id

    stmt = select(MuscleGroup).where(MuscleGroup.id == group.id, MuscleGroup.user_id == other_id)
    result = await session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_unique_set_number_constraint(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 500
    session.add(MuscleGroup(id=3, name="Ноги", emoji="🟣", sort_order=1, is_custom=False))
    session.add(Exercise(id=3, muscle_group_id=3, name="Присед", is_custom=False))
    await session.commit()

    workout = await create_workout(session, user_id=user_id, title="Leg day")
    item = WorkoutExercise(
        workout_id=workout.id,
        exercise_id=3,
        exercise_name_snapshot="Присед",
        order=1,
    )
    session.add(item)
    await session.flush()
    session.add_all(
        [
            SetEntry(workout_exercise_id=item.id, set_number=1, weight=100, reps=10),
            SetEntry(workout_exercise_id=item.id, set_number=1, weight=105, reps=8),
        ]
    )

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_cascade_delete_workout(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 600
    session.add(MuscleGroup(id=4, name="Плечи", emoji="🟡", sort_order=1, is_custom=False))
    session.add(Exercise(id=4, muscle_group_id=4, name="Жим", is_custom=False))
    await session.commit()

    workout = await create_workout(session, user_id=user_id, title="Shoulders")
    item = WorkoutExercise(
        workout_id=workout.id,
        exercise_id=4,
        exercise_name_snapshot="Жим",
        order=1,
    )
    session.add(item)
    await session.flush()
    session.add(SetEntry(workout_exercise_id=item.id, set_number=1, weight=60, reps=12))
    await session.commit()

    await session.delete(workout)
    await session.commit()

    left_item = await session.get(WorkoutExercise, item.id)
    assert left_item is None


@pytest.mark.asyncio
async def test_last_exercise_result_selection(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 700
    session.add(MuscleGroup(id=5, name="Грудь", emoji="🔴", sort_order=1, is_custom=False))
    session.add(Exercise(id=5, muscle_group_id=5, name="Жим лёжа", is_custom=False))
    await session.commit()

    old_workout = Workout(
        user_id=user_id,
        title="Old",
        status=WorkoutStatus.COMPLETED.value,
        date_utc=datetime.now(timezone.utc) - timedelta(days=5),
    )
    new_workout = Workout(
        user_id=user_id,
        title="New",
        status=WorkoutStatus.COMPLETED.value,
        date_utc=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add_all([old_workout, new_workout])
    await session.flush()

    old_item = WorkoutExercise(
        workout_id=old_workout.id,
        exercise_id=5,
        exercise_name_snapshot="Жим лёжа",
        comment="old",
        order=1,
    )
    new_item = WorkoutExercise(
        workout_id=new_workout.id,
        exercise_id=5,
        exercise_name_snapshot="Жим лёжа",
        comment="new",
        order=1,
    )
    session.add_all([old_item, new_item])
    await session.flush()

    session.add_all(
        [
            SetEntry(workout_exercise_id=old_item.id, set_number=1, weight=90, reps=10),
            SetEntry(workout_exercise_id=old_item.id, set_number=2, weight=95, reps=8),
            SetEntry(workout_exercise_id=new_item.id, set_number=1, weight=100, reps=10),
            SetEntry(workout_exercise_id=new_item.id, set_number=2, weight=105, reps=8),
        ]
    )
    await session.commit()

    result = await get_last_exercise_result(session, user_id=user_id, exercise_id=5)
    assert result is not None
    assert result["comment"] == "new"
    assert len(result["sets"]) == 2
    assert result["sets"][0]["weight"] == 100


@pytest.mark.asyncio
async def test_save_exercise_with_empty_comment(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 800
    session.add(MuscleGroup(id=6, name="Руки", emoji="🟢", sort_order=1, is_custom=False))
    session.add(Exercise(id=6, muscle_group_id=6, name="Сгибания", is_custom=False))
    await session.commit()

    workout = await create_workout(session, user_id=user_id, title="Arms")
    item = await add_workout_exercise_with_sets(
        session,
        user_id=user_id,
        workout_id=workout.id,
        exercise_id=6,
        exercise_name_snapshot="Сгибания",
        sets=[{"weight": 25.0, "reps": 12}],
        comment=None,
    )
    assert item.id > 0
    loaded = await get_workout_with_items(session, user_id=user_id, workout_id=workout.id)
    assert loaded is not None
    assert loaded.exercises[0].comment is None
    assert loaded.exercises[0].sets[0].set_number == 1


@pytest.mark.asyncio
async def test_regression_orphan_sets_same_workout_exercise_id(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 900
    session.add(MuscleGroup(id=7, name="Ноги", emoji="🟣", sort_order=1, is_custom=False))
    session.add(Exercise(id=7, muscle_group_id=7, name="Жим ногами", is_custom=False))
    await session.commit()

    workout = await create_workout(session, user_id=user_id, title="Legs")

    # Create and then remove workout_exercise row, leaving stale set row (simulates legacy bad DB state).
    session.add(
        WorkoutExercise(
            id=1,
            workout_id=workout.id,
            exercise_id=7,
            exercise_name_snapshot="Жим ногами",
            order=1,
        )
    )
    await session.flush()
    session.add(SetEntry(workout_exercise_id=1, set_number=1, weight=100, reps=10))
    await session.flush()
    await session.execute(text("DELETE FROM workout_exercises WHERE id = 1"))
    await session.commit()

    item = await add_workout_exercise_with_sets(
        session,
        user_id=user_id,
        workout_id=workout.id,
        exercise_id=7,
        exercise_name_snapshot="Жим ногами",
        sets=[{"weight": 120.0, "reps": 9}],
        comment="ok",
    )
    assert item.id > 0
    loaded = await get_workout_with_items(session, user_id=user_id, workout_id=workout.id)
    assert loaded is not None
    assert len(loaded.exercises) == 1
    assert len(loaded.exercises[0].sets) == 1
    assert loaded.exercises[0].sets[0].set_number == 1


@pytest.mark.asyncio
async def test_list_completed_workouts_with_aggregates(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 1000
    session.add(MuscleGroup(id=8, name="Спина", emoji="🔵", sort_order=1, is_custom=False))
    session.add(Exercise(id=8, muscle_group_id=8, name="Тяга блока", is_custom=False))
    await session.commit()

    in_progress = await create_workout(session, user_id=user_id, title="In progress")
    completed = await create_workout(session, user_id=user_id, title="Completed")
    await complete_workout(session, user_id=user_id, workout_id=completed.id, comment="done")

    await add_workout_exercise_with_sets(
        session,
        user_id=user_id,
        workout_id=completed.id,
        exercise_id=8,
        exercise_name_snapshot="Тяга блока",
        sets=[{"weight": 70.0, "reps": 10}, {"weight": 75.0, "reps": 8}],
        comment=None,
    )

    items, total = await list_completed_workouts(session, user_id=user_id, limit=20, offset=0)
    assert total == 1
    assert len(items) == 1
    assert items[0]["title"] == "Completed"
    assert items[0]["exercise_count"] == 1
    assert items[0]["total_volume"] == 1300.0

    # keep variable used (in_progress was intentionally not completed)
    assert in_progress.status == WorkoutStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_search_completed_workouts_by_exercise_and_period(session) -> None:  # type: ignore[no-untyped-def]
    user_id = 1100
    session.add(MuscleGroup(id=9, name="Грудь", emoji="🔴", sort_order=1, is_custom=False))
    session.add(Exercise(id=9, muscle_group_id=9, name="Жим лёжа", is_custom=False))
    session.add(Exercise(id=10, muscle_group_id=9, name="Разводка", is_custom=False))
    await session.commit()

    old_workout = Workout(
        user_id=user_id,
        title="Old chest",
        status=WorkoutStatus.COMPLETED.value,
        date_utc=datetime.now(timezone.utc) - timedelta(days=120),
    )
    new_workout = Workout(
        user_id=user_id,
        title="New chest",
        status=WorkoutStatus.COMPLETED.value,
        date_utc=datetime.now(timezone.utc) - timedelta(days=5),
    )
    session.add_all([old_workout, new_workout])
    await session.flush()

    session.add_all(
        [
            WorkoutExercise(
                workout_id=old_workout.id,
                exercise_id=10,
                exercise_name_snapshot="Разводка",
                order=1,
            ),
            WorkoutExercise(
                workout_id=new_workout.id,
                exercise_id=9,
                exercise_name_snapshot="Жим лёжа",
                order=1,
            ),
        ]
    )
    await session.commit()

    items, total = await search_completed_workouts(
        session,
        user_id=user_id,
        exercise_id=9,
        date_from=datetime.now(timezone.utc) - timedelta(days=90),
    )
    assert total == 1
    assert len(items) == 1
    assert items[0]["title"] == "New chest"
