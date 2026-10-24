import asyncio
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile, LinkPreviewOptions

from mutagen.id3 import ID3, ID3NoHeaderError, APIC
from mutagen.mp3 import MP3


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не знайдено у файлі .env")

CHANNEL_USERNAME = "uaoldmusic"

POST_FOOTER = (
    "📲 <b>Наші майданчики:</b>\n\n"
    "✈️ <b>Telegram:</b>\n"
    "• https://t.me/uaoldmusic\n"
    "🎬 <b>TikTok:</b>\n"
    "• https://www.tiktok.com/@ua_mussicc/\n"
    "▶️ <b>YouTube:</b>\n"
    "• https://www.youtube.com/@uaoldmusic\n\n"
    "🖤 <b>Підтримуй українську музику — відкривай нове "
    "та ділися тим, що зачепило.</b>\n"
    "<i>Починаємо з музики — будуємо спільноту.</i>"
)

FOOTER_MARKER = "Починаємо з музики — будуємо спільноту."
FOOTER_TEXT = re.sub(r"<[^>]+>", "", POST_FOOTER)


# ============================================================
# ЛОГУВАННЯ
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# TELEGRAM BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher()


# ============================================================
# СТАНИ
# ============================================================

class MusicState(StatesGroup):
    waiting_for_mp3 = State()
    waiting_for_cover = State()


# ============================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# ============================================================

def is_mp3(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".mp3"


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in {
        ".jpg", ".jpeg", ".png"
    }


def get_mime_type(filename: str) -> str:
    if Path(filename).suffix.lower() == ".png":
        return "image/png"

    return "image/jpeg"


def check_mp3(path: Path) -> bool:
    try:
        audio = MP3(path)
        return audio.info is not None
    except Exception:
        return False


def telegram_length(text: str) -> int:
    # Telegram використовує UTF-16 для позицій у тексті.
    # Така перевірка також враховує емодзі.
    return len(text.encode("utf-16-le")) // 2


async def download_telegram_file(
    file_id: str,
    destination: Path,
):
    telegram_file = await bot.get_file(file_id)

    if not telegram_file.file_path:
        raise RuntimeError("Telegram не повернув шлях до файлу.")

    await bot.download_file(
        telegram_file.file_path,
        destination,
    )


async def clear_operation(state: FSMContext):
    data = await state.get_data()
    temp_dir = data.get("temp_dir")

    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)

    await state.clear()


# ============================================================
# ЗАМІНА ОБКЛАДИНКИ
# ============================================================

def replace_cover(mp3_path: Path, image_path: Path):
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("APIC")

    tags.add(
        APIC(
            encoding=3,
            mime=get_mime_type(image_path.name),
            type=3,
            desc="Cover",
            data=image_path.read_bytes(),
        )
    )

    tags.save(mp3_path, v2_version=3)


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start_command(
    message: Message,
    state: FSMContext,
):
    await clear_operation(state)

    await message.answer(
        "🎵 <b>Music Cover Bot</b>\n\n"
        "Надішли мені MP3-файл.\n\n"
        "Після цього я попрошу фотографію, "
        "яку потрібно поставити на обкладинку."
    )

    await state.set_state(MusicState.waiting_for_mp3)


# ============================================================
# /CANCEL
# ============================================================

@dp.message(Command("cancel"))
async def cancel_command(
    message: Message,
    state: FSMContext,
):
    await clear_operation(state)

    await message.answer(
        "❌ Операцію скасовано.\n\n"
        "Для нового треку натисни /start."
    )


# ============================================================
# MP3 ЯК AUDIO
# ============================================================

@dp.message(MusicState.waiting_for_mp3, F.audio)
async def receive_mp3_audio(
    message: Message,
    state: FSMContext,
):
    audio = message.audio

    if not audio:
        return

    filename = audio.file_name or "music.mp3"

    if not is_mp3(filename):
        await message.answer("❌ Потрібен саме MP3-файл.")
        return

    await save_mp3(
        file_id=audio.file_id,
        filename=filename,
        message=message,
        state=state,
    )


# ============================================================
# MP3 ЯК DOCUMENT
# ============================================================

@dp.message(MusicState.waiting_for_mp3, F.document)
async def receive_mp3_document(
    message: Message,
    state: FSMContext,
):
    document = message.document

    if not document:
        return

    filename = document.file_name or ""

    if not is_mp3(filename):
        await message.answer("❌ Потрібен саме MP3-файл.")
        return

    await save_mp3(
        file_id=document.file_id,
        filename=filename,
        message=message,
        state=state,
    )


# ============================================================
# ЗБЕРЕЖЕННЯ MP3
# ============================================================

async def save_mp3(
    file_id: str,
    filename: str,
    message: Message,
    state: FSMContext,
):
    temp_dir = Path(tempfile.mkdtemp(prefix="music_cover_bot_"))

    # Зберігаємо лише ім'я файлу без сторонніх шляхів.
    safe_filename = Path(filename.replace("\\", "/")).name
    mp3_path = temp_dir / safe_filename

    try:
        await message.answer("⏳ Завантажую MP3...")

        await download_telegram_file(file_id, mp3_path)

        if not await asyncio.to_thread(check_mp3, mp3_path):
            shutil.rmtree(temp_dir, ignore_errors=True)

            await message.answer(
                "❌ Не вдалося прочитати цей MP3-файл."
            )
            return

        await state.update_data(
            temp_dir=str(temp_dir),
            mp3_path=str(mp3_path),
            filename=safe_filename,
        )

        await state.set_state(MusicState.waiting_for_cover)

        await message.answer(
            "✅ <b>MP3 отримано!</b>\n\n"
            "🖼 Тепер надішли фотографію, "
            "яку потрібно поставити на обкладинку."
        )

    except Exception:
        logger.exception("Помилка під час завантаження MP3")

        shutil.rmtree(temp_dir, ignore_errors=True)

        await state.clear()
        await state.set_state(MusicState.waiting_for_mp3)

        await message.answer(
            "❌ Сталася помилка під час завантаження MP3.\n"
            "Спробуй надіслати файл ще раз."
        )


# ============================================================
# ФОТО ЯК TELEGRAM PHOTO
# ============================================================

@dp.message(MusicState.waiting_for_cover, F.photo)
async def receive_cover_photo(
    message: Message,
    state: FSMContext,
):
    if not message.photo:
        return

    await process_cover(
        message=message,
        state=state,
        file_id=message.photo[-1].file_id,
        extension=".jpg",
    )


# ============================================================
# ФОТО ЯК JPG / PNG ФАЙЛ
# ============================================================

@dp.message(MusicState.waiting_for_cover, F.document)
async def receive_cover_document(
    message: Message,
    state: FSMContext,
):
    document = message.document

    if not document:
        return

    filename = document.file_name or ""

    if not is_image(filename):
        await message.answer(
            "❌ Надішли фотографію або JPG/PNG-файл."
        )
        return

    await process_cover(
        message=message,
        state=state,
        file_id=document.file_id,
        extension=Path(filename).suffix.lower(),
    )


async def process_cover(
    message: Message,
    state: FSMContext,
    file_id: str,
    extension: str,
):
    data = await state.get_data()

    if not data.get("temp_dir") or not data.get("mp3_path"):
        await clear_operation(state)
        await message.answer(
            "❌ Дані попереднього треку втрачено.\n"
            "Натисни /start і надішли MP3 ще раз."
        )
        return

    cover_path = Path(data["temp_dir"]) / f"cover{extension}"

    try:
        await message.answer("⏳ Вбудовую фотографію в MP3...")

        await download_telegram_file(file_id, cover_path)

    except Exception:
        logger.exception("Помилка під час завантаження обкладинки")

        await message.answer(
            "❌ Не вдалося завантажити фотографію.\n"
            "Спробуй надіслати її ще раз."
        )
        return

    await finish(
        message=message,
        state=state,
        cover_path=cover_path,
    )


# ============================================================
# ФІНАЛЬНА ОБРОБКА
# ============================================================

async def finish(
    message: Message,
    state: FSMContext,
    cover_path: Path,
):
    data = await state.get_data()
    mp3_path = Path(data["mp3_path"])

    try:
        await asyncio.to_thread(
            replace_cover,
            mp3_path,
            cover_path,
        )

        logger.info("Обкладинку успішно додано: %s", mp3_path)

        await message.answer("📤 Готово! Надсилаю MP3...")

        # Обкладинка вже вбудована всередину MP3.
        await message.answer_audio(
            audio=FSInputFile(
                mp3_path,
                filename=mp3_path.name,
            ),
        )

    except Exception:
        logger.exception("Помилка під час обробки MP3")

        await message.answer(
            "❌ Не вдалося обробити або надіслати цей MP3."
        )

    finally:
        await clear_operation(state)

    await message.answer(
        "🔄 Для наступного треку надішли /start."
    )


# ============================================================
# НЕПРАВИЛЬНИЙ ФОРМАТ MP3
# ============================================================

@dp.message(MusicState.waiting_for_mp3)
async def wrong_mp3(message: Message):
    await message.answer(
        "🎵 Я очікую MP3-файл.\n\n"
        "Надішли його як аудіо або документ."
    )


# ============================================================
# НЕПРАВИЛЬНИЙ ФОРМАТ ФОТО
# ============================================================

@dp.message(MusicState.waiting_for_cover)
async def wrong_cover(message: Message):
    await message.answer(
        "🖼 Я очікую фотографію.\n\n"
        "Надішли її як фото або JPG/PNG-файл."
    )


# ============================================================
# АВТОМАТИЧНИЙ ПІДПИС У КАНАЛІ
# ============================================================

def is_music_post(message: Message) -> bool:
    # Пропускаємо всі пости з Telegram Audio.
    if message.audio:
        return True

    # Перевіряємо MP3, надіслані як документ.
    if message.document:
        filename = message.document.file_name or ""
        mime_type = (message.document.mime_type or "").lower()

        return (
            is_mp3(filename)
            or mime_type in {"audio/mpeg", "audio/mp3"}
        )

    return False


@dp.channel_post()
async def add_channel_footer(message: Message):
    username = (message.chat.username or "").lower()

    if username != CHANNEL_USERNAME.lower().lstrip("@"):
        return

    if is_music_post(message):
        return

    original_text = message.text or message.caption or ""

    # Не додаємо підпис, якщо він уже є.
    if FOOTER_MARKER in original_text:
        return

    # Для альбому обробляємо тільки елемент із підписом.
    if message.media_group_id and not message.caption:
        return

    if message.text is not None:
        original_html = message.html_text or ""
        limit = 4096

    elif (
        message.photo
        or message.video
        or message.animation
        or message.document
        or message.voice
    ):
        original_html = message.html_caption or ""
        limit = 1024

    else:
        # Пропускаємо службові повідомлення, опитування тощо.
        return

    separator = "\n\n" if original_text else ""
    visible_text = original_text + separator + FOOTER_TEXT

    if telegram_length(visible_text) > limit:
        logger.warning(
            "Пост %s: підпис не вміщується в ліміт Telegram.",
            message.message_id,
        )
        return

    updated_text = original_html + separator + POST_FOOTER

    try:
        if message.text is not None:
            await message.edit_text(
                text=updated_text,
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(
                    is_disabled=True,
                ),
                reply_markup=message.reply_markup,
            )

        else:
            await message.edit_caption(
                caption=updated_text,
                parse_mode=ParseMode.HTML,
                reply_markup=message.reply_markup,
                show_caption_above_media=(
                    message.show_caption_above_media
                ),
            )

        logger.info(
            "Підпис додано до поста %s",
            message.message_id,
        )

    except (TelegramBadRequest, TelegramForbiddenError):
        logger.exception(
            "Не вдалося додати підпис до поста %s",
            message.message_id,
        )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    logger.info("Music Cover Bot запущено")

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинений.")