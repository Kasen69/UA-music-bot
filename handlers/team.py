from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from config import ADMIN_IDS, ANNOUNCEMENTS_THREAD_ID, COMMUNITY_CHAT_ID
from services.team_service import build_announcement_messages, get_team_mentions

router = Router(name="team")


@router.message(Command("all"), F.chat.type == "private")
async def announce_all_handler(message: Message, command: CommandObject, bot: Bot) -> None:
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        return

    if not command.args or not command.args.strip():
        await message.answer(
            "Напиши текст після команди.\n"
            "Приклад: <code>/all сьогодні о 20:00 зідзвон по контенту</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    mentions = await get_team_mentions(bot)
    if not mentions:
        await message.answer("Не знайдено жодного учасника команди для згадки.")
        return

    messages_to_send = build_announcement_messages(
        text=command.args.strip(),
        mentions=mentions,
        chunk_size=5,
    )

    try:
        for chunk_text in messages_to_send:
            await bot.send_message(
                chat_id=COMMUNITY_CHAT_ID,
                message_thread_id=ANNOUNCEMENTS_THREAD_ID,
                text=chunk_text,
                parse_mode=ParseMode.HTML,
            )
    except TelegramAPIError as e:
        await message.answer(
            f"❌ Помилка під час відправки в спільноту:\n<code>{escape_error(e.message)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer(f"✅ Оголошення надіслано в #Оголошення (згадано: {len(mentions)}).")


def escape_error(err: str) -> str:
    from html import escape
    return escape(err)