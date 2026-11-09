# bot.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers.channel import router as channel_router
from handlers.music import router as music_router
from handlers.rules import router as rules_router
from handlers.birthdays import router as birthdays_router
from handlers.profile import router as profile_router
from services.birthdays import init_birthday_db, setup_birthday_scheduler


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # Ініціалізуємо базу даних днів народжень при запуску
    await init_birthday_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    dp = Dispatcher()

    # Підключаємо всі роутери
    dp.include_routers(
        rules_router,
        channel_router,
        music_router,
        birthdays_router,
        profile_router,
    )

    # Запускаємо фоновий планувальник нагадувань
    setup_birthday_scheduler(bot)

    logging.info("Бот запускається...")

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass