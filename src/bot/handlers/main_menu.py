from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import settings_keyboard
from bot.keyboards.reply import (
    CONTINUE_PREFIX,
    OPEN_MINI_APP,
    SETTINGS,
    START_WORKOUT,
    workout_menu_keyboard,
)
from bot.states import CreateWorkout, WorkoutMenu
from core.config import settings
from db.repositories.users import upsert_user
from db.repositories.workouts import create_workout, get_in_progress_workout
from db.session import SessionLocal

router = Router()


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


@router.message(Command("main"))
async def main_cmd(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    async with SessionLocal() as session:
        await upsert_user(session, message.from_user.id, message.from_user.username)
        in_progress = await get_in_progress_workout(session, message.from_user.id)

    await state.clear()
    title = in_progress.title if in_progress else None
    from bot.keyboards.reply import main_menu_keyboard

    await message.answer("Главное меню", reply_markup=main_menu_keyboard(title))


@router.message(F.text == START_WORKOUT)
async def start_workout(message: Message, state: FSMContext) -> None:
    await _safe_delete_user_message(message)
    await state.set_state(CreateWorkout.waiting_title)
    await message.answer("Введите название тренировки (например, 'День ног'):")


@router.message(CreateWorkout.waiting_title)
async def receive_workout_title(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("Название должно быть не менее 2 символов")
        return

    async with SessionLocal() as session:
        workout = await create_workout(session, message.from_user.id, title)

    await _safe_delete_user_message(message)
    await state.update_data(workout_id=workout.id)
    await state.set_state(WorkoutMenu.active_workout)
    await message.answer(
        f"Тренировка '{title}' создана!",
        reply_markup=workout_menu_keyboard(),
    )


@router.message(F.text.startswith(CONTINUE_PREFIX))
async def continue_workout(message: Message, state: FSMContext) -> None:
    await _safe_delete_user_message(message)
    assert message.from_user is not None
    async with SessionLocal() as session:
        workout = await get_in_progress_workout(session, message.from_user.id)

    if workout is None:
        await message.answer("Незавершённой тренировки нет")
        return

    await state.update_data(workout_id=workout.id)
    await state.set_state(WorkoutMenu.active_workout)
    await message.answer(
        f"Тренировка '{workout.title}' (в процессе)",
        reply_markup=workout_menu_keyboard(),
    )


@router.message(F.text == OPEN_MINI_APP)
async def open_mini_app_stub(message: Message) -> None:
    await _safe_delete_user_message(message)
    if settings.webapp_url:
        await message.answer(
            f"Откройте Mini App кнопкой '{OPEN_MINI_APP}' в главном меню.\n"
            f"Текущий URL: {settings.webapp_url}",
        )
        return
    await message.answer(
        "Mini App еще не настроен. "
        "Добавьте WEBAPP_URL в .env и перезапустите бота."
    )


@router.message(F.text == SETTINGS)
async def open_settings(message: Message) -> None:
    await _safe_delete_user_message(message)
    await message.answer("Настройки пользовательского контента:", reply_markup=settings_keyboard())


@router.callback_query(F.data == "settings_back")
async def settings_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Настройки пользовательского контента:",
        reply_markup=settings_keyboard(),
    )
    await callback.answer()
