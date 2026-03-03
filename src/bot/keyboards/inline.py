from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def muscle_groups_keyboard(groups: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for group in groups:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{group['emoji']} {group['name']}",
                    callback_data=f"mg_select_{group['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить свою группу", callback_data="mg_add_custom")])
    rows.append([InlineKeyboardButton(text="✏️ Управлять своими группами", callback_data="mg_manage_custom")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="mg_back_workout")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def exercises_keyboard(exercises: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for exercise in exercises:
        marker = "📝 " if exercise["has_comment"] else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{marker}{exercise['name']}",
                    callback_data=f"ex_select_{exercise['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить своё упражнение", callback_data="ex_add_custom")])
    rows.append([InlineKeyboardButton(text="✏️ Управлять своими упражнениями", callback_data="ex_manage_custom")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="ex_back_groups")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def set_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚖️ Изменить вес", callback_data="set_change_weight")],
            [InlineKeyboardButton(text="✅ Завершить упражнение", callback_data="set_finish_exercise")],
        ]
    )


def skip_inline_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏭️ Пропустить", callback_data=callback_data)]]
    )


def workout_item_actions_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"we_edit_{item_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"we_delete_{item_id}"),
            ]
        ]
    )


def workout_items_overview_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, item in enumerate(items, 1):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ {idx}. {item['exercise_name_snapshot']}",
                    callback_data=f"we_edit_{item['id']}",
                ),
                InlineKeyboardButton(text="🗑️", callback_data=f"we_delete_{item['id']}"),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_exercise_saved_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Вернуться к редактированию упражнения", callback_data=f"we_edit_{item_id}")],
            [InlineKeyboardButton(text="➕ Добавить ещё упражнение", callback_data="saved_add_more")],
            [InlineKeyboardButton(text="✅ Завершить тренировку", callback_data="saved_finish_workout")],
        ]
    )


def edit_item_keyboard(item_id: int, set_numbers: list[int]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="📝 Изменить комментарий", callback_data=f"we_comment_{item_id}")]]
    for num in set_numbers:
        rows.append(
            [InlineKeyboardButton(text=f"Подход {num}", callback_data=f"we_set_{item_id}_{num}")]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="we_back_view")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_set_keyboard(item_id: int, set_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏋️ Изменить вес", callback_data=f"we_set_weight_{item_id}_{set_number}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔢 Изменить повторения", callback_data=f"we_set_reps_{item_id}_{set_number}"
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"we_edit_{item_id}")],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💪 Мои группы мышц", callback_data="settings_groups")],
            [InlineKeyboardButton(text="🏋️ Мои упражнения", callback_data="settings_exercises")],
        ]
    )


def custom_groups_keyboard(groups: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="➕ Добавить группу", callback_data="cg_add")]
    ]
    for group in groups:
        rows.append(
            [
                InlineKeyboardButton(text=f"{group['name']} ✏️", callback_data=f"cg_edit_{group['id']}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"cg_delete_{group['id']}"),
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def custom_exercises_keyboard(exercises: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="➕ Добавить упражнение", callback_data="ce_add")]
    ]
    for ex in exercises:
        rows.append(
            [
                InlineKeyboardButton(text=f"{ex['name']} ✏️", callback_data=f"ce_edit_{ex['id']}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"ce_delete_{ex['id']}"),
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def custom_groups_manage_keyboard(groups: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="➕ Добавить группу", callback_data="mg_add_custom")]
    ]
    for group in groups:
        rows.append(
            [
                InlineKeyboardButton(text=f"{group['name']} ✏️", callback_data=f"mg_edit_custom_{group['id']}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"mg_delete_custom_{group['id']}"),
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ К группам мышц", callback_data="mg_back_to_groups_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def custom_exercises_manage_keyboard(exercises: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="➕ Добавить упражнение", callback_data="ex_add_custom")]
    ]
    for ex in exercises:
        rows.append(
            [
                InlineKeyboardButton(text=f"{ex['name']} ✏️", callback_data=f"ex_edit_custom_{ex['id']}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"ex_delete_custom_{ex['id']}"),
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ К упражнениям", callback_data="ex_back_to_exercises_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
