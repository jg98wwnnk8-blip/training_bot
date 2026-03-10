from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class WebAppAuthError(Exception):
    pass


class ReplayGuard:
    def __init__(self) -> None:
        self._used: dict[str, int] = {}

    def mark(self, key: str, ttl: int) -> None:
        now = int(time.time())
        self._cleanup(now)
        if key in self._used:
            raise WebAppAuthError("Replay detected")
        self._used[key] = now + ttl

    def _cleanup(self, now: int) -> None:
        expired = [k for k, exp in self._used.items() if exp < now]
        for key in expired:
            self._used.pop(key, None)


replay_guard = ReplayGuard()


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str, bot_token: str, ttl_seconds: int) -> dict:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_value = pairs.pop("hash", None)
    if not hash_value:
        raise WebAppAuthError("Missing hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    expected = hmac.new(_secret_key(bot_token), check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, hash_value):
        raise WebAppAuthError("Invalid signature")

    auth_date = int(pairs.get("auth_date", "0"))
    now = int(time.time())
    if auth_date <= 0 or now - auth_date > ttl_seconds:
        raise WebAppAuthError("Expired auth_date")

    replay_guard.mark(hash_value, ttl_seconds)

    user_raw = pairs.get("user")
    if not user_raw:
        raise WebAppAuthError("Missing user")
    user = json.loads(user_raw)
    return user


def issue_access_token(user_id: int, ttl_seconds: int, secret: str) -> str:
    exp = int(time.time()) + ttl_seconds
    payload = json.dumps({"sub": user_id, "exp": exp}, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_access_token(token: str, secret: str) -> dict:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError as exc:
        raise WebAppAuthError("Invalid token format") from exc

    expected = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise WebAppAuthError("Invalid token signature")

    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except Exception as exc:  # noqa: BLE001
        raise WebAppAuthError("Invalid token payload") from exc

    exp = int(payload.get("exp", 0))
    if exp <= int(time.time()):
        raise WebAppAuthError("Token expired")
    if "sub" not in payload:
        raise WebAppAuthError("Token missing subject")
    return payload
