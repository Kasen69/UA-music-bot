from pathlib import Path

from aiogram import Bot


async def download_telegram_file(
    bot: Bot,
    file_id: str,
    destination: Path,
):
    telegram_file = await bot.get_file(file_id)

    if not telegram_file.file_path:
        raise RuntimeError(
            "Telegram не повернув шлях до файлу."
        )

    await bot.download_file(
        telegram_file.file_path,
        destination,
    )