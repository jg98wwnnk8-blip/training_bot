from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import custom_exercises_keyboard, custom_groups_keyboard, edit_item_keyboard, edit_set_keyboard
from bot.states import EditExerciseName, EditMuscleGroup, EditWorkoutExercise
from db.repositories.catalog import (
    create_custom_exercise,
    create_custom_muscle_group,
    delete_custom_exercise,
    delete_custom_muscle_group,
    get_custom_exercises,
    get_custom_muscle_groups,
    rename_custom_exercise,
    rename_custom_muscle_group,
)
from db.repositories.workouts import (
    get_workout_item,
    update_set_reps,
    update_set_weight,
    update_workout_item_comment,
)
from db.session import SessionLocal
from services.validators import is_valid_reps, is_valid_weight, parse_number

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


async def _render_custom_groups(callback: CallbackQuery, state: FSMContext, user_id: int) -> None:
    async with SessionLocal() as session:
        groups = await get_custom_muscle_groups(session, user_id)
    view = [{"id": g.id, "name": g.name} for g in groups]
    await _render_anchor_from_callback(
        callback,
        state,
        "Мои пользовательские группы:",
        custom_groups_keyboard(view),
    )


async def _render_custom_exercises(callback: CallbackQuery, state: FSMContext, user_id: int) -> None:
    async with SessionLocal() as session:
        exercises = await get_custom_exercises(session, user_id)
    view = [{"id": e.id, "name": e.name} for e in exercises]
    await _render_anchor_from_callback(
        callback,
        state,
        "Мои пользовательские упражнения:",
        custom_exercises_keyboard(view),
    )


@router.callback_query(F.data == "settings_groups")
async def settings_groups(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    await _render_custom_groups(callback, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "settings_exercises")
async def settings_exercises(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    await _render_custom_exercises(callback, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "cg_add")
async def add_group_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(group_mode="create")
    await state.set_state(EditMuscleGroup.waiting_name)
    await _render_anchor_from_callback(callback, state, "Введите название новой группы мышц:")
    await callback.answer()


@router.callback_query(F.data.startswith("cg_edit_"))
async def edit_group_start(callback: CallbackQuery, state: FSMContext) -> None:
    group_id = int((callback.data or "").split("_")[-1])
    await state.update_data(group_mode="edit", group_id=group_id)
    await state.set_state(EditMuscleGroup.waiting_name)
    await _render_anchor_from_callback(callback, state, "Введите новое название группы:")
    await callback.answer()


@router.callback_query(F.data.startswith("cg_delete_"))
async def delete_group(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    group_id = int((callback.data or "").split("_")[-1])
    async with SessionLocal() as session:
        ok = await delete_custom_muscle_group(session, callback.from_user.id, group_id)
    if ok:
        await _render_custom_groups(callback, state, callback.from_user.id)
    await callback.answer("Удалено" if ok else "Недоступно", show_alert=False)


@router.message(EditMuscleGroup.waiting_name)
async def save_group_name(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    new_name = (message.text or "").strip()
    if len(new_name) < 2:
        await _render_anchor_from_message(
            message,
            state,
            "Название должно быть не менее 2 символов. Введите новое значение:",
        )
        await _safe_delete_user_message(message)
        return

    data = await state.get_data()
    mode = data.get("group_mode")
    async with SessionLocal() as session:
        if mode == "edit":
            ok = await rename_custom_muscle_group(
                session, message.from_user.id, int(data["group_id"]), new_name
            )
            status = "✅ Группа обновлена" if ok else "❌ Не удалось обновить"
        else:
            await create_custom_muscle_group(session, message.from_user.id, new_name)
            status = "✅ Группа добавлена"
        groups = await get_custom_muscle_groups(session, message.from_user.id)

    await _safe_delete_user_message(message)
    view = [{"id": g.id, "name": g.name} for g in groups]
    await _render_anchor_from_message(message, state, status, custom_groups_keyboard(view))
    await state.set_state(None)


@router.callback_query(F.data == "ce_add")
async def add_exercise_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(exercise_mode="create")
    await state.set_state(EditExerciseName.waiting_name)
    await _render_anchor_from_callback(callback, state, "Введите: <id_группы> <название упражнения>")
    await callback.answer()


@router.callback_query(F.data.startswith("ce_edit_"))
async def edit_exercise_start(callback: CallbackQuery, state: FSMContext) -> None:
    exercise_id = int((callback.data or "").split("_")[-1])
    await state.update_data(exercise_mode="edit", exercise_id=exercise_id)
    await state.set_state(EditExerciseName.waiting_name)
    await _render_anchor_from_callback(callback, state, "Введите новое название упражнения:")
    await callback.answer()


@router.callback_query(F.data.startswith("ce_delete_"))
async def delete_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.from_user is not None
    exercise_id = int((callback.data or "").split("_")[-1])
    async with SessionLocal() as session:
        ok = await delete_custom_exercise(session, callback.from_user.id, exercise_id)
    if ok:
        await _render_custom_exercises(callback, state, callback.from_user.id)
    await callback.answer("Удалено" if ok else "Недоступно", show_alert=False)


@router.message(EditExerciseName.waiting_name)
async def save_exercise_name(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    text = (message.text or "").strip()
    data = await state.get_data()
    mode = data.get("exercise_mode")

    async with SessionLocal() as session:
        if mode == "edit":
            ok = await rename_custom_exercise(
                session, message.from_user.id, int(data["exercise_id"]), text
            )
            status = "✅ Упражнение обновлено" if ok else "❌ Не удалось обновить"
        else:
            parts = text.split(" ", 1)
            if len(parts) != 2 or not parts[0].isdigit():
                await _render_anchor_from_message(
                    message,
                    state,
                    "Формат: <id_группы> <название>. Попробуйте снова:",
                )
                await _safe_delete_user_message(message)
                return
            muscle_group_id = int(parts[0])
            name = parts[1].strip()
            if len(name) < 2:
                await _render_anchor_from_message(
                    message,
                    state,
                    "Название должно быть не менее 2 символов. Попробуйте снова:",
                )
                await _safe_delete_user_message(message)
                return
            await create_custom_exercise(session, message.from_user.id, muscle_group_id, name)
            status = "✅ Упражнение добавлено"

        exercises = await get_custom_exercises(session, message.from_user.id)

    await _safe_delete_user_message(message)
    view = [{"id": e.id, "name": e.name} for e in exercises]
    await _render_anchor_from_message(message, state, status, custom_exercises_keyboard(view))
    await state.set_state(None)


@router.callback_query(F.data.startswith("we_comment_"))
async def edit_item_comment_start(callback: CallbackQuery, state: FSMContext) -> None:
    item_id = int((callback.data or "").split("_")[-1])
    await state.update_data(edit_item_id=item_id)
    await state.set_state(EditWorkoutExercise.waiting_comment)
    await _render_anchor_from_callback(callback, state, "Введите новый комментарий к упражнению:")
    await callback.answer()


@router.message(EditWorkoutExercise.waiting_comment)
async def edit_item_comment_save(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    data = await state.get_data()
    item_id = int(data["edit_item_id"])
    comment = (message.text or "").strip() or None
    async with SessionLocal() as session:
        ok = await update_workout_item_comment(session, message.from_user.id, item_id, comment)
        item = await get_workout_item(session, message.from_user.id, item_id)

    await _safe_delete_user_message(message)
    if item is None:
        await _render_anchor_from_message(message, state, "Элемент не найден")
    else:
        set_numbers = sorted([s.set_number for s in item.sets])
        await _render_anchor_from_message(
            message,
            state,
            "✅ Комментарий обновлён" if ok else "❌ Не удалось обновить",
            edit_item_keyboard(item_id, set_numbers),
        )
    await state.set_state(None)


@router.callback_query(F.data.startswith("we_set_"))
async def edit_set_choose(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split("_")
    if len(parts) != 4:
        await callback.answer()
        return
    _, _, item_id, set_number = parts
    await _render_anchor_from_callback(
        callback,
        state,
        f"Что изменить в подходе {set_number}?",
        edit_set_keyboard(int(item_id), int(set_number)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("we_set_weight_"))
async def edit_set_weight_start(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, item_id, set_number = (callback.data or "").split("_")
    await state.update_data(edit_item_id=int(item_id), edit_set_number=int(set_number))
    await state.set_state(EditWorkoutExercise.waiting_set_weight)
    await _render_anchor_from_callback(callback, state, "Введите новый вес (0.5..500):")
    await callback.answer()


@router.callback_query(F.data.startswith("we_set_reps_"))
async def edit_set_reps_start(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, _, item_id, set_number = (callback.data or "").split("_")
    await state.update_data(edit_item_id=int(item_id), edit_set_number=int(set_number))
    await state.set_state(EditWorkoutExercise.waiting_set_reps)
    await _render_anchor_from_callback(callback, state, "Введите новые повторения (1..200):")
    await callback.answer()


@router.message(EditWorkoutExercise.waiting_set_weight)
async def edit_set_weight_save(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    text = (message.text or "").strip()
    if not is_valid_weight(text):
        await _render_anchor_from_message(message, state, "❌ Некорректный вес. Введите 0.5..500:")
        await _safe_delete_user_message(message)
        return

    value = parse_number(text)
    assert value is not None
    data = await state.get_data()
    item_id = int(data["edit_item_id"])
    async with SessionLocal() as session:
        ok = await update_set_weight(
            session,
            message.from_user.id,
            item_id,
            int(data["edit_set_number"]),
            value,
        )
        item = await get_workout_item(session, message.from_user.id, item_id)

    await _safe_delete_user_message(message)
    if item is None:
        await _render_anchor_from_message(message, state, "Элемент не найден")
    else:
        set_numbers = sorted([s.set_number for s in item.sets])
        await _render_anchor_from_message(
            message,
            state,
            "✅ Вес обновлён" if ok else "❌ Не удалось обновить",
            edit_item_keyboard(item_id, set_numbers),
        )
    await state.set_state(None)


@router.message(EditWorkoutExercise.waiting_set_reps)
async def edit_set_reps_save(message: Message, state: FSMContext) -> None:
    assert message.from_user is not None
    text = (message.text or "").strip()
    if not is_valid_reps(text):
        await _render_anchor_from_message(message, state, "❌ Некорректные повторения. Введите 1..200:")
        await _safe_delete_user_message(message)
        return

    data = await state.get_data()
    item_id = int(data["edit_item_id"])
    async with SessionLocal() as session:
        ok = await update_set_reps(
            session,
            message.from_user.id,
            item_id,
            int(data["edit_set_number"]),
            int(text),
        )
        item = await get_workout_item(session, message.from_user.id, item_id)

    await _safe_delete_user_message(message)
    if item is None:
        await _render_anchor_from_message(message, state, "Элемент не найден")
    else:
        set_numbers = sorted([s.set_number for s in item.sets])
        await _render_anchor_from_message(
            message,
            state,
            "✅ Повторения обновлены" if ok else "❌ Не удалось обновить",
            edit_item_keyboard(item_id, set_numbers),
        )
    await state.set_state(None)
