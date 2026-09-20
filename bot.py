import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile

from mutagen.id3 import ID3, ID3NoHeaderError, APIC
from mutagen.mp3 import MP3


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "❌ BOT_TOKEN не знайдено у файлі .env"
    )


# ============================================================
# ЛОГУВАННЯ
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# TELEGRAM BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
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
    """
    Перевіряє розширення файлу.
    """

    return Path(filename).suffix.lower() == ".mp3"


def is_image(filename: str) -> bool:
    """
    Перевіряє, чи є файл зображенням.
    """

    return Path(filename).suffix.lower() in {
        ".jpg",
        ".jpeg",
        ".png"
    }


def get_mime_type(filename: str) -> str:
    """
    Визначає MIME-тип картинки.
    """

    extension = Path(filename).suffix.lower()

    if extension in {".jpg", ".jpeg"}:
        return "image/jpeg"

    if extension == ".png":
        return "image/png"

    return "image/jpeg"


def check_mp3(path: Path) -> bool:
    """
    Перевіряє, чи файл є коректним MP3.
    """

    try:
        audio = MP3(path)

        return audio.info is not None

    except Exception:
        return False


async def download_telegram_file(
    file_id: str,
    destination: Path
):
    """
    Завантажує файл із Telegram
    у вказаний локальний шлях.
    """

    telegram_file = await bot.get_file(
        file_id
    )

    if not telegram_file.file_path:
        raise RuntimeError(
            "Telegram не повернув шлях до файлу."
        )

    await bot.download_file(
        telegram_file.file_path,
        destination
    )


# ============================================================
# ЗАМІНА ОБКЛАДИНКИ
# ============================================================

def replace_cover(
    mp3_path: Path,
    image_path: Path
):
    """
    Видаляє стару обкладинку MP3
    та додає нову.

    Інші ID3-метадані не змінюються.
    """

    # --------------------------------------------------------
    # Отримуємо існуючі ID3-теги
    # --------------------------------------------------------

    try:
        tags = ID3(mp3_path)

    except ID3NoHeaderError:
        tags = ID3()

    # --------------------------------------------------------
    # Видаляємо стару обкладинку
    # --------------------------------------------------------

    tags.delall("APIC")

    # --------------------------------------------------------
    # Читаємо нову картинку
    # --------------------------------------------------------

    image_data = image_path.read_bytes()

    mime_type = get_mime_type(
        image_path.name
    )

    # --------------------------------------------------------
    # Додаємо нову обкладинку
    # --------------------------------------------------------

    tags.add(
        APIC(
            encoding=3,
            mime=mime_type,
            type=3,          # Front Cover
            desc="Cover",
            data=image_data
        )
    )

    # --------------------------------------------------------
    # Зберігаємо метадані
    # --------------------------------------------------------

    tags.save(
        mp3_path,
        v2_version=3
    )


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start_command(
    message: Message,
    state: FSMContext
):
    """
    Запускає процес.
    """

    # Видаляємо старі тимчасові файли,
    # якщо вони залишилися.
    data = await state.get_data()

    old_temp_dir = data.get(
        "temp_dir"
    )

    if old_temp_dir:
        shutil.rmtree(
            old_temp_dir,
            ignore_errors=True
        )

    await state.clear()

    await message.answer(
        "🎵 <b>Music Cover Bot</b>\n\n"
        "Надішли мені MP3-файл.\n\n"
        "Після цього я попрошу фотографію, "
        "яку потрібно поставити на обкладинку."
    )

    await state.set_state(
        MusicState.waiting_for_mp3
    )


# ============================================================
# /CANCEL
# ============================================================

@dp.message(Command("cancel"))
async def cancel_command(
    message: Message,
    state: FSMContext
):
    """
    Скасовує поточну операцію.
    """

    data = await state.get_data()

    temp_dir = data.get(
        "temp_dir"
    )

    if temp_dir:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

    await state.clear()

    await message.answer(
        "❌ Операцію скасовано.\n\n"
        "Для нового треку натисни /start."
    )


# ============================================================
# MP3 ЯК AUDIO
# ============================================================

@dp.message(
    MusicState.waiting_for_mp3,
    F.audio
)
async def receive_mp3_audio(
    message: Message,
    state: FSMContext
):
    """
    Отримує MP3, відправлений
    як звичайне Telegram Audio.
    """

    audio = message.audio

    if not audio:
        return

    filename = (
        audio.file_name
        or "music.mp3"
    )

    if not is_mp3(filename):
        await message.answer(
            "❌ Потрібен саме MP3-файл."
        )
        return

    await save_mp3(
        file_id=audio.file_id,
        filename=filename,
        message=message,
        state=state
    )


# ============================================================
# MP3 ЯК DOCUMENT
# ============================================================

@dp.message(
    MusicState.waiting_for_mp3,
    F.document
)
async def receive_mp3_document(
    message: Message,
    state: FSMContext
):
    """
    Отримує MP3, відправлений
    як Telegram Document.
    """

    document = message.document

    if not document:
        return

    filename = (
        document.file_name
        or ""
    )

    if not is_mp3(filename):
        await message.answer(
            "❌ Потрібен саме MP3-файл."
        )
        return

    await save_mp3(
        file_id=document.file_id,
        filename=filename,
        message=message,
        state=state
    )


# ============================================================
# ЗБЕРЕЖЕННЯ MP3
# ============================================================

async def save_mp3(
    file_id: str,
    filename: str,
    message: Message,
    state: FSMContext
):
    """
    Завантажує MP3 та переводить
    бота в режим очікування фото.
    """

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="music_cover_bot_"
        )
    )

    mp3_path = (
        temp_dir / filename
    )

    try:

        await message.answer(
            "⏳ Завантажую MP3..."
        )

        # Завантаження MP3
        await download_telegram_file(
            file_id,
            mp3_path
        )

        # Перевірка MP3
        if not check_mp3(mp3_path):

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            await message.answer(
                "❌ Не вдалося прочитати "
                "цей MP3-файл."
            )

            return

        # Зберігаємо інформацію
        await state.update_data(
            temp_dir=str(temp_dir),
            mp3_path=str(mp3_path),
            filename=filename
        )

        await message.answer(
            "✅ <b>MP3 отримано!</b>\n\n"
            "🖼 Тепер надішли фотографію, "
            "яку потрібно поставити "
            "на обкладинку."
        )

        await state.set_state(
            MusicState.waiting_for_cover
        )

    except Exception:

        logger.exception(
            "Помилка під час завантаження MP3"
        )

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        await message.answer(
            "❌ Сталася помилка під час "
            "завантаження MP3."
        )


# ============================================================
# ФОТО ЯК TELEGRAM PHOTO
# ============================================================

@dp.message(
    MusicState.waiting_for_cover,
    F.photo
)
async def receive_cover_photo(
    message: Message,
    state: FSMContext
):
    """
    Отримує звичайне Telegram-фото.
    """

    if not message.photo:
        return

    # Беремо найбільшу версію
    photo = message.photo[-1]

    data = await state.get_data()

    temp_dir = Path(
        data["temp_dir"]
    )

    cover_path = (
        temp_dir / "cover.jpg"
    )

    try:

        await message.answer(
            "⏳ Вбудовую фотографію "
            "в MP3..."
        )

        await download_telegram_file(
            photo.file_id,
            cover_path
        )

        await finish(
            message=message,
            state=state,
            cover_path=cover_path
        )

    except Exception:

        logger.exception(
            "Помилка під час обробки фото"
        )

        await message.answer(
            "❌ Не вдалося обробити "
            "фотографію."
        )


# ============================================================
# ФОТО ЯК JPG / PNG ФАЙЛ
# ============================================================

@dp.message(
    MusicState.waiting_for_cover,
    F.document
)
async def receive_cover_document(
    message: Message,
    state: FSMContext
):
    """
    Отримує JPG / JPEG / PNG,
    відправлений як файл.
    """

    document = message.document

    if not document:
        return

    filename = (
        document.file_name
        or ""
    )

    if not is_image(filename):

        await message.answer(
            "❌ Надішли фотографію "
            "або JPG/PNG-файл."
        )

        return

    data = await state.get_data()

    temp_dir = Path(
        data["temp_dir"]
    )

    extension = Path(
        filename
    ).suffix.lower()

    cover_path = (
        temp_dir
        / f"cover{extension}"
    )

    try:

        await message.answer(
            "⏳ Вбудовую фотографію "
            "в MP3..."
        )

        await download_telegram_file(
            document.file_id,
            cover_path
        )

        await finish(
            message=message,
            state=state,
            cover_path=cover_path
        )

    except Exception:

        logger.exception(
            "Помилка під час обробки обкладинки"
        )

        await message.answer(
            "❌ Не вдалося обробити "
            "фотографію."
        )


# ============================================================
# ФІНАЛЬНА ОБРОБКА
# ============================================================

async def finish(
    message: Message,
    state: FSMContext,
    cover_path: Path
):
    """
    Вбудовує обкладинку в MP3
    та повертає файл користувачу.
    """

    data = await state.get_data()

    temp_dir = Path(
        data["temp_dir"]
    )

    mp3_path = Path(
        data["mp3_path"]
    )

    try:

        # ----------------------------------------------------
        # ВБУДОВУЄМО ОБКЛАДИНКУ
        # ----------------------------------------------------

        replace_cover(
            mp3_path,
            cover_path
        )

        logger.info(
            "Обкладинку успішно додано: %s",
            mp3_path
        )

        # ----------------------------------------------------
        # ПОВІДОМЛЕННЯ
        # ----------------------------------------------------

        await message.answer(
            "📤 Готово! Надсилаю MP3..."
        )

        # ----------------------------------------------------
        # НАЗВА БЕЗ .MP3
        # ----------------------------------------------------

        telegram_filename = (
            mp3_path.stem
        )

        # ----------------------------------------------------
        # ПОВЕРТАЄМО MP3
        # ----------------------------------------------------

        await message.answer_audio(
            audio=FSInputFile(
                mp3_path,
                filename=telegram_filename
            ),

            # Передаємо обкладинку
            # окремо Telegram
            thumbnail=FSInputFile(
                cover_path
            ),
        )

    except Exception as e:

        logger.exception(
            "Помилка під час обробки MP3: %s",
            e
        )

        await message.answer(
            "❌ Не вдалося додати "
            "обкладинку до цього MP3."
        )

    finally:

        # ----------------------------------------------------
        # ВИДАЛЯЄМО ТИМЧАСОВІ ФАЙЛИ
        # ----------------------------------------------------

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        await state.clear()

        await message.answer(
            "🔄 Для наступного треку "
            "надішли /start."
        )


# ============================================================
# НЕПРАВИЛЬНИЙ ФОРМАТ MP3
# ============================================================

@dp.message(
    MusicState.waiting_for_mp3
)
async def wrong_mp3(
    message: Message
):
    await message.answer(
        "🎵 Я очікую MP3-файл.\n\n"
        "Надішли його як аудіо "
        "або документ."
    )


# ============================================================
# НЕПРАВИЛЬНИЙ ФОРМАТ ФОТО
# ============================================================

@dp.message(
    MusicState.waiting_for_cover
)
async def wrong_cover(
    message: Message
):
    await message.answer(
        "🖼 Я очікую фотографію.\n\n"
        "Надішли її як фото "
        "або JPG/PNG-файл."
    )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    logger.info(
        "Music Cover Bot запущено"
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info(
            "Бот зупинений."
        )
