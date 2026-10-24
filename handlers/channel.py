import logging
import re
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message, LinkPreviewOptions
from config import CHANNEL_USERNAME
from services.music import is_mp3

logger = logging.getLogger(__name__)
router = Router(name='channel')

POST_FOOTER = (
    '📲 <b>Наші майданчики:</b>\n\n'
    '✈️ <b>Telegram:</b>\n'
    '• https://t.me/uaoldmusic\n'
    '🎬 <b>TikTok:</b>\n'
    '• https://www.tiktok.com/@ua_mussicc/\n'
    '▶️ <b>YouTube:</b>\n'
    '• https://www.youtube.com/@uaoldmusic\n\n'
    '🖤 <b>Підтримуй українську музику — відкривай нове '
    'та ділися тим, що зачепило.</b>\n'
    '<i>Починаємо з музики — будуємо спільноту.</i>'
)
FOOTER_MARKER = 'Починаємо з музики — будуємо спільноту.'
FOOTER_TEXT = re.sub(r'<[^>]+>', '', POST_FOOTER)


def is_music_post(message: Message) -> bool:
    if message.audio:
        return True
    document = message.document
    return bool(document and (
        is_mp3(document.file_name or '')
        or (document.mime_type or '').lower() in {'audio/mpeg', 'audio/mp3'}
    ))


@router.channel_post()
async def add_channel_footer(message: Message):
    if (message.chat.username or '').lower() != CHANNEL_USERNAME:
        return
    if is_music_post(message):
        return
    original = message.text or message.caption or ''
    if FOOTER_MARKER in original:
        return
    if message.media_group_id and not message.caption:
        return
    if message.text is not None:
        original_html, limit = message.html_text or '', 4096
    elif (message.photo or message.video or message.animation
          or message.document or message.voice):
        original_html, limit = message.html_caption or '', 1024
    else:
        return
    separator = '\n\n' if original else ''
    visible = original + separator + FOOTER_TEXT
    if len(visible.encode('utf-16-le')) // 2 > limit:
        logger.warning('Підпис не вміщується у пост %s', message.message_id)
        return
    updated = original_html + separator + POST_FOOTER
    try:
        if message.text is not None:
            await message.edit_text(
                text=updated, parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
                reply_markup=message.reply_markup,
            )
        else:
            await message.edit_caption(
                caption=updated, parse_mode=ParseMode.HTML,
                reply_markup=message.reply_markup,
                show_caption_above_media=message.show_caption_above_media,
            )
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.exception('Не вдалося підписати пост %s', message.message_id)
