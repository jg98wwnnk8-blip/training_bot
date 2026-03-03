from fastapi import FastAPI, HTTPException

from api.schemas import WebAppAuthRequest, WebAppAuthResponse
from core.config import settings
from services.webapp_auth import WebAppAuthError, issue_access_token, validate_init_data

app = FastAPI(title="Workout Bot API", version="0.1.0")


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
