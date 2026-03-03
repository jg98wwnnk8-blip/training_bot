# Workout Bot Backend

Backend MVP for Telegram workout tracking bot.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
python -m bot.main
```

## API

```bash
uvicorn api.app:app --reload
```

Endpoints:
- `GET /health`
- `POST /auth/webapp`
- `GET /workouts`
- `GET /workouts/{workout_id}`
- `GET /workouts/search`
- `GET /filters`

## Cloud Deploy (Render + Postgres)

This repo includes `render.yaml` with:
- PostgreSQL (`workout-postgres`)
- Web service (`workout-api`)
- Worker service (`workout-bot`)

### Deploy steps

1. Push backend repo to GitHub.
2. In Render, create a **Blueprint** and select this backend repo.
3. Render will create DB + services from `render.yaml`.
4. Set env vars in both services:
   - `BOT_TOKEN=<telegram bot token>`
   - `WEBAPP_URL=https://<your-miniapp>.vercel.app` (set after Vercel deploy)
   - `API_CORS_ORIGINS=https://<your-miniapp>.vercel.app`
5. Keep `DATABASE_URL` managed by Blueprint (`fromDatabase`).
6. Deploy both services.

### Runtime commands (already wired in `render.yaml`)

- API start:
```bash
alembic upgrade head && uvicorn api.app:app --host 0.0.0.0 --port $PORT
```
- Bot start:
```bash
alembic upgrade head && python -m bot.main
```

## Mini App integration env

- `DATABASE_URL` accepts:
  - `sqlite+aiosqlite:///./workouts.db` (local)
  - `postgresql+asyncpg://...` (cloud)
- If provider gives `postgres://...`, config auto-converts to `postgresql+asyncpg://...`.
- `WEBAPP_URL` controls Telegram `📱 Открыть приложение` button target.
- `API_CORS_ORIGINS` must contain Vercel frontend origin.

## Local fallback (Cloudflare tunnel, optional)

Use only for local preview if cloud is not ready:
1. Run API locally.
2. Expose with `cloudflared tunnel --url http://localhost:8000`.
3. Run Mini App locally.
4. Expose frontend with `cloudflared tunnel --url http://localhost:5173`.
5. Put frontend tunnel URL into `WEBAPP_URL` and `API_CORS_ORIGINS`.

## Smoke Checklist (MVP)

1. `/start` shows welcome and main menu.
2. `➕ Записать тренировку` creates an `in_progress` workout.
3. `➕ Добавить упражнение`:
   - choose muscle group,
   - choose exercise,
   - enter weight/reps for at least one set,
   - finish exercise with:
     - text comment,
     - `⏭️ Пропустить`.
4. After saving exercise, buttons work:
   - `↩️ Вернуться к редактированию упражнения`
   - `➕ Добавить ещё упражнение`
   - `✅ Завершить тренировку`
5. Workout completion works both ways:
   - text comment,
   - inline skip button.
6. `👁️ Просмотреть тренировку` shows current workout and allows edit/delete actions.
7. Custom catalog:
   - add/edit/delete custom muscle groups,
   - add/edit/delete custom exercises,
   - verify isolation by `user_id` (another user does not see them).
8. Chat hygiene:
   - reply-button user messages are auto-removed,
   - main flow is rendered in one anchor message (minimal clutter).

## Release

Create MVP tag when tests/checks pass:

```bash
git add .
git commit -m "feat: MVP bot core with FSM, CRUD, and anchor UX"
git tag -a v0.1.0-mvp -m "Workout Bot MVP core"
git push origin main --tags
```
