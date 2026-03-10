from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    FiltersResponse,
    SearchResponse,
    WebAppAuthRequest,
    WebAppAuthResponse,
    WorkoutDetailResponse,
    WorkoutListResponse,
)
from aiogram.types import Update

import logging

from bot.app import create_bot_and_dispatcher
from core.config import settings
from core.logging import setup_logging
from db.repositories.catalog import get_filter_catalog
from db.repositories.workouts import (
    get_workout_detail_payload,
    list_completed_workouts,
    search_completed_workouts,
)
from db.seed import seed_system_catalog
from db.session import SessionLocal
from services.webapp_auth import (
    WebAppAuthError,
    issue_access_token,
    validate_init_data,
    verify_access_token,
)

app = FastAPI(title="Workout Bot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
bot, dp = create_bot_and_dispatcher()


@app.on_event("startup")
async def on_startup() -> None:
    setup_logging(settings.log_level)
    async with SessionLocal() as session:
        try:
            await seed_system_catalog(session)
        except Exception:
            logger.exception("Seed catalog failed on startup")
    if settings.webhook_url:
        await bot.set_webhook(settings.webhook_url, drop_pending_updates=True)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await bot.session.close()


@app.post(settings.webhook_path)
async def telegram_webhook(update: dict) -> dict:
    update_obj = Update.model_validate(update)
    await dp.feed_update(bot, update_obj)
    return {"ok": True}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/webapp", response_model=WebAppAuthResponse)
async def auth_webapp(payload: WebAppAuthRequest) -> WebAppAuthResponse:
    try:
        user = validate_init_data(
            init_data=payload.initData,
            bot_token=settings.bot_token,
            ttl_seconds=settings.webapp_auth_ttl_seconds,
        )
    except WebAppAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = int(user["id"])
    token = issue_access_token(
        user_id=user_id,
        ttl_seconds=settings.webapp_access_token_ttl_seconds,
        secret=settings.bot_token,
    )
    return WebAppAuthResponse(
        access_token=token,
        expires_in=settings.webapp_access_token_ttl_seconds,
        user_id=user_id,
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1].strip()


async def get_current_user_id(authorization: str | None = Header(default=None)) -> int:
    token = _extract_bearer_token(authorization)
    try:
        payload = verify_access_token(token, settings.bot_token)
    except WebAppAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return int(payload["sub"])


@app.get("/workouts", response_model=WorkoutListResponse)
async def list_workouts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user_id),
) -> WorkoutListResponse:
    async with SessionLocal() as session:
        items, total = await list_completed_workouts(
            session,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
    return WorkoutListResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/workouts/search", response_model=SearchResponse)
async def search_workouts(
    muscle_group_id: int | None = Query(default=None, ge=1),
    exercise_id: int | None = Query(default=None, ge=1),
    period_months: int | None = Query(default=None, ge=1, le=24),
    user_id: int = Depends(get_current_user_id),
) -> SearchResponse:
    date_from = None
    if period_months is not None:
        date_from = datetime.now(UTC) - timedelta(days=period_months * 30)

    async with SessionLocal() as session:
        items, total = await search_completed_workouts(
            session,
            user_id=user_id,
            muscle_group_id=muscle_group_id,
            exercise_id=exercise_id,
            date_from=date_from,
        )
    return SearchResponse(items=items, total=total)


@app.get("/workouts/{workout_id}", response_model=WorkoutDetailResponse)
async def workout_detail(
    workout_id: int,
    user_id: int = Depends(get_current_user_id),
) -> WorkoutDetailResponse:
    async with SessionLocal() as session:
        payload = await get_workout_detail_payload(session, user_id=user_id, workout_id=workout_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    return WorkoutDetailResponse(**payload)


@app.get("/filters", response_model=FiltersResponse)
async def filters(user_id: int = Depends(get_current_user_id)) -> FiltersResponse:
    async with SessionLocal() as session:
        payload = await get_filter_catalog(session, user_id=user_id)
    return FiltersResponse(**payload)
