from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards.reply import main_menu_keyboard
from db.repositories.users import upsert_user
from db.repositories.workouts import get_in_progress_workout
from db.session import SessionLocal

router = Router()


@router.message(Command("start"))
async def start_cmd(message: Message) -> None:
    assert message.from_user is not None
    async with SessionLocal() as session:
        await upsert_user(session, message.from_user.id, message.from_user.username)
        in_progress = await get_in_progress_workout(session, message.from_user.id)

    in_progress_title = in_progress.title if in_progress else None
    await message.answer(
        "Привет! Я помогу вести журнал тренировок.",
        reply_markup=main_menu_keyboard(in_progress_title),
    )
