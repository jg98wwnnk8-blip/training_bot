from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import (
    edit_item_keyboard,
    skip_inline_keyboard,
    workout_items_overview_keyboard,
)
from bot.keyboards.reply import (
    WORKOUT_ADD_EXERCISE,
    WORKOUT_BACK_MAIN,
    WORKOUT_FINISH,
    WORKOUT_VIEW,
    main_menu_keyboard,
    workout_menu_keyboard,
)
from bot.states import FinishWorkout
from db.repositories.workouts import (
    complete_workout,
    delete_workout_item,
    get_workout_item,
    get_workout_with_items,
)
from db.session import SessionLocal
from services.formatters import format_workout_overview

router = Router()
ANCHOR_MESSAGE_ID_KEY = "ui_anchor_message_id"


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def _render_anchor_from_message(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
) -> None:
    data = await state.get_data()
    anchor_id = data.get(ANCHOR_MESSAGE_ID_KEY)
    if anchor_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=int(anchor_id),
                text=text,
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass

    sent = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(**{ANCHOR_MESSAGE_ID_KEY: sent.message_id})


async def _render_anchor_from_callback(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup=None,
) -> None:
    if callback.message:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        await state.update_data(**{ANCHOR_MESSAGE_ID_KEY: callback.message.message_id})


async def _build_workout_view(user_id: int, workout_id: int) -> tuple[str, list[dict]]:
    async with SessionLocal() as session:
        workout = await get_workout_with_items(session, user_id, workout_id)

    if workout is None:
        return "Тренировка не найдена", []

    items: list[dict] = []
    for item in sorted(workout.exercises, key=lambda x: x.order):
        sets = [{"weight": s.weight, "reps": s.reps, "set_number": s.set_number} for s in item.sets]
        items.append(
            {
                "id": item.id,
                "exercise_name_snapshot": item.exercise_name_snapshot,
                "sets": sorted(sets, key=lambda x: x["set_number"]),
                "comment": item.comment,
            }
        )

    text = format_workout_overview(workout.title, items)
    return text, items


@router.message(F.text == WORKOUT_ADD_EXERCISE)
async def add_exercise_entry(message: Message, state: FSMContext) -> None:
    from bot.handlers.exercise_flow import show_muscle_groups

    await _safe_delete_user_message(message)
    await show_muscle_groups(message, state)


@router.message(F.text == WORKOUT_VIEW)
async def view_current_workout(message: Message, state: FSMContext) -> None:
    await _safe_delete_user_message(message)
    assert message.from_user is not None
    data = await state.get_data()
    workout_id = data.get("workout_id")
    if not workout_id:
        await message.answer("Нет активной тренировки")
        return

    text, items = await _build_workout_view(message.from_user.id, int(workout_id))
    await _render_anchor_from_message(
        message,
        state,
        text,
        workout_items_overview_keyboard(items) if items else None,
    )


@router.message(F.text == WORKOUT_FINISH)
async def finish_workout_start(message: Message, state: FSMContext) -> None:
    await _safe_delete_user_message(message)
    await state.set_state(FinishWorkout.waiting_comment_optional)
    await _render_anchor_from_message(
        message,
        state,
        "Введите комментарий к тренировке (опционально):",
        skip_inline_keyboard("wf_skip_comment"),
    )


async def _complete_workout_by_user(
    *,
    user_id: int,
    state: FSMContext,
    comment: str | None,
) -> str:
    data = await state.get_data()
    workout_id = data.get("workout_id")
    if not workout_id:
        raise ValueError("Нет активной тренировки")

    async with SessionLocal() as session:
        ok = await complete_workout(session, user_id, int(workout_id), comment)
        workout = await get_workout_with_items(session, user_id, int(workout_id))

    if not ok:
        raise ValueError("Не удалось завершить тренировку")

    title = workout.title if workout else "Тренировка"
    await state.clear()
    return f"✅ {title} завершена!"


@router.message(FinishWorkout.waiting_comment_optional)
async def finish_workout_with_comment(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    text = (message.text or "").strip()
    comment = None if text in {"⏭️ Пропустить", ""} else text
    try:
        result_text = await _complete_workout_by_user(
            user_id=message.from_user.id,
            state=state,
            comment=comment,
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await _safe_delete_user_message(message)
    await _render_anchor_from_message(
        message,
        state,
        result_text,
    )
    await message.answer("Главное меню", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "wf_skip_comment")
async def finish_workout_skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    try:
        result_text = await _complete_workout_by_user(
            user_id=callback.from_user.id,
            state=state,
            comment=None,
        )
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await _render_anchor_from_callback(callback, state, result_text)
    if callback.message:
        await callback.message.answer("Главное меню", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(F.text == WORKOUT_BACK_MAIN)
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    await _safe_delete_user_message(message)
    assert message.from_user is not None
    data = await state.get_data()
    title = None
    workout_id = data.get("workout_id")
    if workout_id:
        async with SessionLocal() as session:
            workout = await get_workout_with_items(session, message.from_user.id, int(workout_id))
            title = workout.title if workout else None

    await state.clear()
    await message.answer(
        "Возврат в главное меню. Тренировка сохранена как незавершённая.",
        reply_markup=main_menu_keyboard(title),
    )


@router.callback_query(F.data.startswith("we_delete_"))
async def delete_workout_item_callback(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    item_id = int((callback.data or "").split("_")[-1])

    async with SessionLocal() as session:
        ok = await delete_workout_item(session, callback.from_user.id, item_id)

    if not ok:
        await callback.answer("Не удалось удалить", show_alert=True)
        return

    data = await state.get_data()
    workout_id = data.get("workout_id")
    if not workout_id:
        await callback.answer("Нет активной тренировки", show_alert=True)
        return

    text, items = await _build_workout_view(callback.from_user.id, int(workout_id))
    await _render_anchor_from_callback(
        callback,
        state,
        text,
        workout_items_overview_keyboard(items) if items else None,
    )
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("we_edit_"))
async def edit_workout_item(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    item_id = int((callback.data or "").split("_")[-1])
    async with SessionLocal() as session:
        item = await get_workout_item(session, callback.from_user.id, item_id)

    if item is None:
        await callback.answer("Элемент не найден", show_alert=True)
        return

    set_numbers = sorted([s.set_number for s in item.sets])
    await _render_anchor_from_callback(
        callback,
        state,
        f"✏️ Редактирование: {item.exercise_name_snapshot}",
        edit_item_keyboard(item.id, set_numbers),
    )
    await callback.answer()


@router.callback_query(F.data == "we_back_view")
async def back_from_edit(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    data = await state.get_data()
    workout_id = data.get("workout_id")
    if not workout_id:
        await callback.answer("Нет активной тренировки", show_alert=True)
        return

    text, items = await _build_workout_view(callback.from_user.id, int(workout_id))
    await _render_anchor_from_callback(
        callback,
        state,
        text,
        workout_items_overview_keyboard(items) if items else None,
    )
    await callback.answer()
