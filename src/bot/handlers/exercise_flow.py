from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
import logging

from bot.keyboards.inline import (
    after_exercise_saved_keyboard,
    custom_exercises_manage_keyboard,
    custom_groups_manage_keyboard,
    exercises_keyboard,
    muscle_groups_keyboard,
    set_actions_keyboard,
    skip_inline_keyboard,
)
from bot.keyboards.reply import workout_menu_keyboard
from bot.states import AddExercise, AddSet, FinishWorkout, WorkoutMenu
from db.repositories.catalog import (
    create_custom_exercise,
    create_custom_muscle_group,
    delete_custom_exercise,
    delete_custom_muscle_group,
    get_custom_exercises_by_group,
    get_custom_muscle_groups,
    get_exercises_by_group_with_comment_flag,
    get_muscle_groups_for_user,
    rename_custom_exercise,
    rename_custom_muscle_group,
)
from db.repositories.workouts import add_workout_exercise_with_sets, get_last_exercise_result
from db.session import SessionLocal
from services.formatters import format_previous_exercise_result
from services.validators import is_valid_reps, is_valid_weight, parse_number

router = Router()
ANCHOR_MESSAGE_ID_KEY = "ui_anchor_message_id"
logger = logging.getLogger(__name__)


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def _render_anchor_from_message(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
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
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if callback.message:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        await state.update_data(**{ANCHOR_MESSAGE_ID_KEY: callback.message.message_id})


async def _render_muscle_groups_to_message(message: Message, state: FSMContext, user_id: int) -> None:
    async with SessionLocal() as session:
        groups = await get_muscle_groups_for_user(session, user_id)
    view = [{"id": g.id, "name": g.name, "emoji": g.emoji} for g in groups]
    await _render_anchor_from_message(
        message,
        state,
        "Выберите группу мышц:",
        muscle_groups_keyboard(view),
    )


async def _render_muscle_groups_to_callback(
    callback: CallbackQuery, state: FSMContext, user_id: int
) -> None:
    async with SessionLocal() as session:
        groups = await get_muscle_groups_for_user(session, user_id)
    view = [{"id": g.id, "name": g.name, "emoji": g.emoji} for g in groups]
    await _render_anchor_from_callback(
        callback,
        state,
        "Выберите группу мышц:",
        muscle_groups_keyboard(view),
    )


async def _render_exercises_list(
    callback: CallbackQuery, state: FSMContext, user_id: int, muscle_group_id: int
) -> None:
    async with SessionLocal() as session:
        exercises = await get_exercises_by_group_with_comment_flag(session, user_id, muscle_group_id)
    await _render_anchor_from_callback(
        callback,
        state,
        "Выберите упражнение:\n\n📝 — есть комментарий с прошлой тренировки",
        exercises_keyboard(exercises),
    )


async def _save_current_exercise(
    *,
    user_id: int,
    state: FSMContext,
    comment: str | None,
) -> int:
    data = await state.get_data()
    workout_id = data.get("workout_id")
    exercise_id = data.get("exercise_id")
    exercise_name = data.get("exercise_name")
    sets = data.get("sets", [])

    if not workout_id or not exercise_id or not sets:
        raise ValueError("Недостаточно данных для сохранения упражнения")

    async with SessionLocal() as session:
        item = await add_workout_exercise_with_sets(
            session,
            user_id=user_id,
            workout_id=workout_id,
            exercise_id=exercise_id,
            exercise_name_snapshot=str(exercise_name),
            sets=sets,
            comment=comment,
        )
    await state.update_data(exercise_id=None, exercise_name=None, sets=[], current_weight=None)
    await state.set_state(WorkoutMenu.active_workout)
    return item.id


async def show_muscle_groups(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    data = await state.get_data()
    if not data.get("workout_id"):
        await message.answer("Сначала создайте тренировку")
        return

    await state.set_state(AddExercise.waiting_muscle_group)
    await _render_muscle_groups_to_message(message, state, message.from_user.id)


@router.callback_query(F.data == "mg_back_workout")
async def back_mg(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer("Меню тренировки", reply_markup=workout_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "mg_back_to_groups_list")
async def back_to_groups_list(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    await state.set_state(AddExercise.waiting_muscle_group)
    await _render_muscle_groups_to_callback(callback, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "mg_add_custom")
async def add_custom_group_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddExercise.waiting_custom_group_name)
    await _render_anchor_from_callback(callback, state, "Введите название новой группы мышц:")
    await callback.answer()


@router.callback_query(F.data == "mg_manage_custom")
async def manage_custom_groups(callback: CallbackQuery) -> None:
    assert callback.from_user is not None
    async with SessionLocal() as session:
        groups = await get_custom_muscle_groups(session, callback.from_user.id)
    view = [{"id": g.id, "name": g.name} for g in groups]
    if callback.message:
        await callback.message.edit_text(
            "Управление своими группами:",
            reply_markup=custom_groups_manage_keyboard(view),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("mg_edit_custom_"))
async def edit_custom_group_start(callback: CallbackQuery, state: FSMContext) -> None:
    group_id = int((callback.data or "").split("_")[-1])
    await state.update_data(edit_custom_group_id=group_id)
    await state.set_state(AddExercise.waiting_custom_group_rename)
    await _render_anchor_from_callback(callback, state, "Введите новое название группы:")
    await callback.answer()


@router.callback_query(F.data.startswith("mg_delete_custom_"))
async def delete_custom_group_action(callback: CallbackQuery) -> None:
    assert callback.from_user is not None
    group_id = int((callback.data or "").split("_")[-1])
    async with SessionLocal() as session:
        await delete_custom_muscle_group(session, callback.from_user.id, group_id)
        groups = await get_custom_muscle_groups(session, callback.from_user.id)
    view = [{"id": g.id, "name": g.name} for g in groups]
    if callback.message:
        await callback.message.edit_text(
            "Управление своими группами:",
            reply_markup=custom_groups_manage_keyboard(view),
        )
    await callback.answer("Удалено")


@router.message(AddExercise.waiting_custom_group_name)
async def add_custom_group_save(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Название должно быть не менее 2 символов")
        return

    async with SessionLocal() as session:
        await create_custom_muscle_group(session, message.from_user.id, name)

    await _safe_delete_user_message(message)
    await state.set_state(AddExercise.waiting_muscle_group)
    await _render_muscle_groups_to_message(message, state, message.from_user.id)


@router.message(AddExercise.waiting_custom_group_rename)
async def edit_custom_group_save(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Название должно быть не менее 2 символов")
        return

    data = await state.get_data()
    group_id = int(data.get("edit_custom_group_id", 0))
    async with SessionLocal() as session:
        await rename_custom_muscle_group(session, message.from_user.id, group_id, name)

    await _safe_delete_user_message(message)
    await state.set_state(AddExercise.waiting_muscle_group)
    await _render_muscle_groups_to_message(message, state, message.from_user.id)


@router.callback_query(F.data.startswith("mg_select_"))
async def select_muscle_group(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    muscle_group_id = int((callback.data or "").split("_")[-1])
    await state.update_data(muscle_group_id=muscle_group_id)
    await state.set_state(AddExercise.waiting_exercise)
    await _render_exercises_list(callback, state, callback.from_user.id, muscle_group_id)
    await callback.answer()


@router.callback_query(F.data == "ex_back_groups")
async def back_exercises_to_groups(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    await state.set_state(AddExercise.waiting_muscle_group)
    await _render_muscle_groups_to_callback(callback, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "ex_back_to_exercises_list")
async def back_to_exercises_list(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    data = await state.get_data()
    muscle_group_id = int(data.get("muscle_group_id", 0))
    if muscle_group_id:
        await state.set_state(AddExercise.waiting_exercise)
        await _render_exercises_list(callback, state, callback.from_user.id, muscle_group_id)
    await callback.answer()


@router.callback_query(F.data == "ex_add_custom")
async def add_custom_exercise_start(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("muscle_group_id"):
        await callback.answer("Сначала выберите группу мышц", show_alert=True)
        return
    await state.set_state(AddExercise.waiting_custom_exercise_name)
    await _render_anchor_from_callback(callback, state, "Введите название нового упражнения:")
    await callback.answer()


@router.callback_query(F.data == "ex_manage_custom")
async def manage_custom_exercises(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    data = await state.get_data()
    muscle_group_id = int(data.get("muscle_group_id", 0))
    if not muscle_group_id:
        await callback.answer("Сначала выберите группу мышц", show_alert=True)
        return

    async with SessionLocal() as session:
        exercises = await get_custom_exercises_by_group(session, callback.from_user.id, muscle_group_id)
    view = [{"id": e.id, "name": e.name} for e in exercises]
    if callback.message:
        await callback.message.edit_text(
            "Управление своими упражнениями в этой группе:",
            reply_markup=custom_exercises_manage_keyboard(view),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ex_edit_custom_"))
async def edit_custom_exercise_start(callback: CallbackQuery, state: FSMContext) -> None:
    exercise_id = int((callback.data or "").split("_")[-1])
    await state.update_data(edit_custom_exercise_id=exercise_id)
    await state.set_state(AddExercise.waiting_custom_exercise_rename)
    await _render_anchor_from_callback(callback, state, "Введите новое название упражнения:")
    await callback.answer()


@router.callback_query(F.data.startswith("ex_delete_custom_"))
async def delete_custom_exercise_action(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    exercise_id = int((callback.data or "").split("_")[-1])
    data = await state.get_data()
    muscle_group_id = int(data.get("muscle_group_id", 0))
    async with SessionLocal() as session:
        await delete_custom_exercise(session, callback.from_user.id, exercise_id)
        exercises = await get_custom_exercises_by_group(session, callback.from_user.id, muscle_group_id)

    view = [{"id": e.id, "name": e.name} for e in exercises]
    if callback.message:
        await callback.message.edit_text(
            "Управление своими упражнениями в этой группе:",
            reply_markup=custom_exercises_manage_keyboard(view),
        )
    await callback.answer("Удалено")


@router.message(AddExercise.waiting_custom_exercise_name)
async def add_custom_exercise_save(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Название должно быть не менее 2 символов")
        return

    data = await state.get_data()
    muscle_group_id = int(data.get("muscle_group_id", 0))
    if not muscle_group_id:
        await message.answer("Сначала выберите группу мышц")
        return

    async with SessionLocal() as session:
        await create_custom_exercise(session, message.from_user.id, muscle_group_id, name)
        exercises = await get_exercises_by_group_with_comment_flag(
            session, message.from_user.id, muscle_group_id
        )

    await _safe_delete_user_message(message)
    await state.set_state(AddExercise.waiting_exercise)
    await _render_anchor_from_message(
        message,
        state,
        "Упражнение добавлено. Выберите упражнение:",
        exercises_keyboard(exercises),
    )


@router.message(AddExercise.waiting_custom_exercise_rename)
async def edit_custom_exercise_save(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Название должно быть не менее 2 символов")
        return

    data = await state.get_data()
    exercise_id = int(data.get("edit_custom_exercise_id", 0))
    muscle_group_id = int(data.get("muscle_group_id", 0))
    async with SessionLocal() as session:
        await rename_custom_exercise(session, message.from_user.id, exercise_id, name)
        exercises = await get_exercises_by_group_with_comment_flag(
            session, message.from_user.id, muscle_group_id
        )

    await _safe_delete_user_message(message)
    await state.set_state(AddExercise.waiting_exercise)
    await _render_anchor_from_message(
        message,
        state,
        "Упражнение обновлено. Выберите упражнение:",
        exercises_keyboard(exercises),
    )


@router.callback_query(F.data.startswith("ex_select_"))
async def select_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    exercise_id = int((callback.data or "").split("_")[-1])

    async with SessionLocal() as session:
        previous = await get_last_exercise_result(session, callback.from_user.id, exercise_id)
        exercises = await get_exercises_by_group_with_comment_flag(
            session, callback.from_user.id, (await state.get_data())["muscle_group_id"]
        )

    selected = next((e for e in exercises if e["id"] == exercise_id), None)
    if selected is None:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    text = "Введите вес в килограммах (например: 100):"
    prev = format_previous_exercise_result(previous)
    if prev:
        text = f"{prev}\n\n{text}"

    await state.update_data(exercise_id=exercise_id, exercise_name=selected["name"], sets=[])
    await state.set_state(AddSet.waiting_weight)
    await _render_anchor_from_callback(callback, state, text)
    await callback.answer()


@router.message(AddSet.waiting_weight)
async def receive_weight(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not is_valid_weight(text):
        await message.answer("❌ Введите корректный вес в диапазоне 0.5..500")
        return

    value = parse_number(text)
    assert value is not None
    await state.update_data(current_weight=value)

    data = await state.get_data()
    set_number = len(data.get("sets", [])) + 1
    await state.set_state(AddSet.waiting_reps)
    await _safe_delete_user_message(message)
    await _render_anchor_from_message(
        message,
        state,
        f"Введите количество повторений для подхода {set_number}:",
    )


@router.message(AddSet.waiting_reps)
async def receive_reps(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not is_valid_reps(text):
        await message.answer("❌ Введите целое число повторений 1..200")
        return

    reps = int(text)
    data = await state.get_data()
    current_weight = float(data["current_weight"])
    sets = list(data.get("sets", []))
    sets.append({"weight": current_weight, "reps": reps})
    await state.update_data(sets=sets)

    set_number = len(sets)
    await _safe_delete_user_message(message)
    await _render_anchor_from_message(
        message,
        state,
        f"✅ Подход {set_number}: {current_weight} кг × {reps}\n\n"
        f"Введите количество повторений для подхода {set_number + 1}:",
        set_actions_keyboard(),
    )


@router.callback_query(F.data == "set_change_weight")
async def change_weight(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddSet.waiting_weight)
    data = await state.get_data()
    next_set = len(data.get("sets", [])) + 1
    await _render_anchor_from_callback(callback, state, f"Введите новый вес для подхода {next_set}:")
    await callback.answer()


@router.callback_query(F.data == "set_finish_exercise")
async def finish_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("sets"):
        await callback.answer("Сначала добавьте хотя бы один подход", show_alert=True)
        return
    await state.set_state(AddExercise.waiting_comment_optional)
    await _render_anchor_from_callback(
        callback,
        state,
        "Добавьте комментарий к упражнению (опционально).\nИли нажмите кнопку ниже.",
        skip_inline_keyboard("set_skip_comment"),
    )
    await callback.answer()


@router.message(AddExercise.waiting_comment_optional)
async def save_exercise(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    text = (message.text or "").strip()
    comment = None if text in {"⏭️ Пропустить", ""} else text
    try:
        item_id = await _save_current_exercise(user_id=message.from_user.id, state=state, comment=comment)
    except ValueError:
        await message.answer("Недостаточно данных для сохранения упражнения")
        return
    except Exception as exc:
        logger.exception("save_exercise failed")
        await message.answer(f"Ошибка сохранения упражнения: {exc}")
        return
    await _safe_delete_user_message(message)
    await _render_anchor_from_message(
        message,
        state,
        "✅ Упражнение сохранено",
        after_exercise_saved_keyboard(item_id),
    )


@router.callback_query(F.data == "set_skip_comment")
async def skip_exercise_comment(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    try:
        item_id = await _save_current_exercise(user_id=callback.from_user.id, state=state, comment=None)
    except ValueError:
        await callback.answer("Недостаточно данных для сохранения", show_alert=True)
        return
    except Exception as exc:
        logger.exception("skip_exercise_comment failed")
        await callback.answer(f"Ошибка сохранения: {exc}", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            "✅ Упражнение сохранено",
            reply_markup=after_exercise_saved_keyboard(item_id),
        )
    await callback.answer()


@router.callback_query(F.data == "saved_add_more")
async def saved_add_more(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    await state.set_state(AddExercise.waiting_muscle_group)
    await _render_muscle_groups_to_callback(callback, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "saved_finish_workout")
async def saved_finish_workout(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FinishWorkout.waiting_comment_optional)
    await _render_anchor_from_callback(
        callback,
        state,
        "Введите комментарий к тренировке (опционально):",
        skip_inline_keyboard("wf_skip_comment"),
    )
    await callback.answer()
