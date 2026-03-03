from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types.web_app_info import WebAppInfo

from core.config import settings

START_WORKOUT = "➕ Записать тренировку"
OPEN_MINI_APP = "📱 Открыть приложение"
SETTINGS = "⚙️ Настройки"
CONTINUE_PREFIX = "🔄 Продолжить тренировку"


WORKOUT_ADD_EXERCISE = "➕ Добавить упражнение"
WORKOUT_VIEW = "👁️ Просмотреть тренировку"
WORKOUT_FINISH = "✅ Завершить тренировку"
WORKOUT_BACK_MAIN = "◀️ Назад в главное меню"


SKIP = "⏭️ Пропустить"


def main_menu_keyboard(in_progress_title: str | None = None) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=START_WORKOUT)]]
    if in_progress_title:
        rows.append([KeyboardButton(text=f"{CONTINUE_PREFIX} '{in_progress_title}'")])
    if settings.webapp_url:
        rows.append(
            [
                KeyboardButton(
                    text=OPEN_MINI_APP,
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        )
    else:
        rows.append([KeyboardButton(text=OPEN_MINI_APP)])
    rows.append([KeyboardButton(text=SETTINGS)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def workout_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=WORKOUT_ADD_EXERCISE)],
            [KeyboardButton(text=WORKOUT_VIEW)],
            [KeyboardButton(text=WORKOUT_FINISH)],
            [KeyboardButton(text=WORKOUT_BACK_MAIN)],
        ],
        resize_keyboard=True,
    )


def skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=SKIP)]], resize_keyboard=True)
