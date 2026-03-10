# Changelog

## v0.2.0-cloud-ready - 2026-03-03

### Added
- Render Blueprint config (`render.yaml`) for:
  - `workout-api` web service,
  - `workout-bot` worker,
  - free PostgreSQL instance.
- Unit tests for database URL normalization in settings (`tests/unit/test_config.py`).

### Changed
- Added `asyncpg` dependency for PostgreSQL async runtime.
- Added settings normalization for provider URLs:
  - `postgres://...` -> `postgresql+asyncpg://...`
  - `postgresql://...` -> `postgresql+asyncpg://...`
- Updated backend README for cloud-first deploy flow (Render + Postgres + Vercel Mini App).
- Added webhook mode for Telegram bot inside `workout-api` (Render free plan compatible).

## v0.1.0-mvp - 2026-03-03

### Added
- Initial backend repository structure for Telegram workout bot.
- Aiogram bot with FSM-based workout flow.
- FastAPI app with `GET /health` and `POST /auth/webapp` stub.
- SQLAlchemy models, repositories, and Alembic migration `0001_init`.
- Seed data for system muscle groups and exercises.
- Inline/reply keyboards for workout recording, edit, and settings.
- Rate-limit and structured event logging middlewares.
- Unit and integration tests for validators, formatters, and repository logic.
- GitHub Actions CI pipeline (`ruff`, `mypy`, `pytest`).

### Changed
- Implemented anchor-message UX for core workout/add/edit flows to reduce chat clutter.
- Added inline skip buttons for optional comments.
- Added previous exercise result preview (sets + comment) before entering weight.
- Added auto-delete of reply-button user messages in main interaction paths.
- Added webhook reset before polling startup.

### Fixed
- Alembic async URL issue (`MissingGreenlet`) by converting async URL to sync for migrations.
- Logging format crash due to missing custom fields (`action`, `user_id`, `chat_id`).
- Telegram polling conflict hardening by explicit webhook deletion on start.
- Exercise save regression with SQLite uniqueness conflict on `sets(workout_exercise_id, set_number)`:
  - enabled SQLite foreign keys via `PRAGMA foreign_keys=ON`,
  - added defensive cleanup for stale orphan rows before set insert.
