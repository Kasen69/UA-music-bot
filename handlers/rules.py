from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

router = Router(name="rules")

# Встав сюди посилання на опубліковані правила.
RULES_URL = "https://telegra.ph/Pravila-sp%D1%96lnoti-Kulturnij-shum-10-26"


@router.message(Command("rules"))
async def show_rules(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 Правила спільноти",
                    url=RULES_URL,
                )
            ]
        ]
    )

    await message.answer(
        "🔊 <b>Правила спільноти «Культурний шум»</b>\n\n"
        "Поважай людей, підтримуй творчість і допомагай "
        "українській культурі звучати голосніше.\n\n"
        "Повні правила — за кнопкою нижче 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )