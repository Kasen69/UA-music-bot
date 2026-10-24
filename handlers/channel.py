import logging

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message, LinkPreviewOptions

from config import CHANNEL_USERNAME
from services.music import is_mp3


logger = logging.getLogger(__name__)
router = Router(name="channel")

COMMENT_TEXT = (
    "📲 <b>Наші майданчики:</b>\n\n"
    "✈️ <b>Telegram:</b>\n"
    "• https://t.me/uaoldmusic\n"
    "🎬 <b>TikTok:</b>\n"
    "• https://www.tiktok.com/@ua_mussicc/\n"
    "▶️ <b>YouTube:</b>\n"
    "• https://www.youtube.com/@uaoldmusic\n"
    "📸 <b>Instagram:</b>\n"
    "• https://www.instagram.com/uamussicc/\n\n"
    "🖤 <b>Підтримуй українську музику — відкривай нове "
    "та ділися тим, що зачепило.</b>\n"
    "<i>Починаємо з музики — будуємо спільноту.</i>"
)


def is_music_post(message: Message) -> bool:
    if message.audio:
        return True

    document = message.document

    if document:
        filename = document.file_name or ""
        mime_type = (document.mime_type or "").lower()

        return (
            is_mp3(filename)
            or mime_type.startswith("audio/")
        )

    return False


@router.message(F.is_automatic_forward == True)
async def comment_music_post(message: Message):
    # Отримуємо канал, з якого пост потрапив
    # до прив'язаної групи обговорення.
    channel = message.sender_chat

    if not channel:
        return

    username = (channel.username or "").lower()
    target = CHANNEL_USERNAME.lstrip("@").lower()

    if username != target:
        return

    # Пишемо лише під музичними файлами.
    if not is_music_post(message):
        return

    try:
        # Відповідь на пересланий пост у групі
        # з'явиться в коментарях до поста каналу.
        await message.reply(
            text=COMMENT_TEXT,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(
                is_disabled=True,
            ),
        )

    except Exception:
        logger.exception(
            "Не вдалося додати коментар під музикою: %s",
            message.message_id,
        )