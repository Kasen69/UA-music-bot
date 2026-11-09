# handlers/profile.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("id"))
async def cmd_get_my_id(message: Message):
    user_id = message.from_user.id
    await message.answer(
        f"🆔 Ваш унікальний Telegram ID:\n`{user_id}`\n\n"
        f"Він використовується системою для прив'язки ваших днів народжень та надсилання нагадувань.",
        parse_mode="Markdown"
    )