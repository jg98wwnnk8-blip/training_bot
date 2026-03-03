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
