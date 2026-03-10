from __future__ import annotations

import asyncio
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import api.app as api_app_module
from core.config import settings
from db.models import Base, Exercise, MuscleGroup, SetEntry, User, Workout, WorkoutExercise, WorkoutStatus
from services.webapp_auth import issue_access_token


def _seed_sync(maker: async_sessionmaker) -> None:
    async def _seed() -> None:
        async with maker() as session:
            session.add(User(id=1, username="tester", timezone_name="UTC"))
            session.add(MuscleGroup(id=1, name="Грудь", emoji="🔴", sort_order=1, is_custom=False))
            session.add(MuscleGroup(id=2, name="Спина", emoji="🔵", sort_order=2, is_custom=False))
            session.add(Exercise(id=11, muscle_group_id=1, name="Жим лёжа", is_custom=False))
            session.add(Exercise(id=12, muscle_group_id=2, name="Тяга блока", is_custom=False))

            session.add(
                Workout(
                    id=101,
                    user_id=1,
                    title="Грудь + трицепс",
                    status=WorkoutStatus.COMPLETED.value,
                    comment="Хорошая тренировка",
                )
            )
            session.add(
                Workout(
                    id=102,
                    user_id=1,
                    title="В процессе",
                    status=WorkoutStatus.IN_PROGRESS.value,
                )
            )
            session.add(
                WorkoutExercise(
                    id=1001,
                    workout_id=101,
                    exercise_id=11,
                    exercise_name_snapshot="Жим лёжа",
                    comment="Можно прибавить",
                    order=1,
                )
            )
            session.add_all(
                [
                    SetEntry(workout_exercise_id=1001, set_number=1, weight=100.0, reps=10),
                    SetEntry(workout_exercise_id=1001, set_number=2, weight=105.0, reps=8),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


@pytest.fixture()
def app_client() -> Generator[TestClient, None, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async def _prepare() -> async_sessionmaker:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    maker = asyncio.run(_prepare())
    _seed_sync(maker)

    api_app_module.SessionLocal = maker
    api_app_module.app.dependency_overrides[api_app_module.get_current_user_id] = lambda: 1

    with TestClient(api_app_module.app) as client:
        yield client

    api_app_module.app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_health_endpoint(app_client: TestClient) -> None:
    response = app_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_workouts_requires_auth_header_without_override() -> None:
    api_app_module.app.dependency_overrides.clear()
    with TestClient(api_app_module.app) as client:
        response = client.get("/workouts")
        assert response.status_code == 401


def test_list_workouts(app_client: TestClient) -> None:
    response = app_client.get("/workouts?limit=20&offset=0")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["title"] == "Грудь + трицепс"


def test_workout_detail(app_client: TestClient) -> None:
    response = app_client.get("/workouts/101")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 101
    assert len(payload["exercises"]) == 1
    assert len(payload["exercises"][0]["sets"]) == 2


def test_workout_search(app_client: TestClient) -> None:
    response = app_client.get("/workouts/search?exercise_id=11&period_months=6")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == 101


def test_filters(app_client: TestClient) -> None:
    response = app_client.get("/filters")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["name"] == "Грудь" for item in payload["muscle_groups"])
    assert any(item["name"] == "Жим лёжа" for item in payload["exercises"])


def test_invalid_bearer_token_rejected() -> None:
    api_app_module.app.dependency_overrides.clear()
    with TestClient(api_app_module.app) as client:
        response = client.get("/workouts", headers={"Authorization": "Bearer bad.token"})
        assert response.status_code == 401


def test_expired_bearer_token_rejected() -> None:
    api_app_module.app.dependency_overrides.clear()
    expired_token = issue_access_token(user_id=1, ttl_seconds=-1, secret=settings.bot_token)
    with TestClient(api_app_module.app) as client:
        response = client.get("/workouts", headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401


def test_workout_detail_404(app_client: TestClient) -> None:
    response = app_client.get("/workouts/999999")
    assert response.status_code == 404
