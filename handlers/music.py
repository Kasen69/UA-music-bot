
import logging
import shutil
import tempfile

from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from states import MusicState
from services.files import download_telegram_file
from services.music import (
    is_mp3,
    is_image,
    check_mp3,
    replace_cover,
)


logger = logging.getLogger(__name__)
router = Router(name="music")


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    data = await state.get_data()

    old_temp_dir = data.get("temp_dir")

    if old_temp_dir:
        shutil.rmtree(old_temp_dir, ignore_errors=True)

    await state.clear()

    await message.answer(
        "🎵 <b>Music Cover Bot</b>\n\n"
        "Надішли мені MP3-файл.\n\n"
        "Після цього я попрошу фотографію, "
        "яку потрібно поставити на обкладинку."
    )

    await state.set_state(MusicState.waiting_for_mp3)


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    data = await state.get_data()

    temp_dir = data.get("temp_dir")

    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)

    await state.clear()

    await message.answer(
        "❌ Операцію скасовано.\n\n"
        "Для нового треку натисни /start."
    )


# ==========================================
# ОТРИМАННЯ MP3 ЯК AUDIO
# ==========================================

@router.message(MusicState.waiting_for_mp3, F.audio)
async def receive_mp3_audio(message: Message, state: FSMContext):
    audio = message.audio

    if not audio:
        return

    filename = audio.file_name

    if not filename:
        filename = f"{audio.title or 'music'}.mp3"

    if not is_mp3(filename):
        await message.answer("❌ Потрібен саме MP3-файл.")
        return

    await save_mp3(
        file_id=audio.file_id,
        filename=filename,
        message=message,
        state=state,
    )


# ==========================================
# ОТРИМАННЯ MP3 ЯК DOCUMENT
# ==========================================

@router.message(MusicState.waiting_for_mp3, F.document)
async def receive_mp3_document(message: Message, state: FSMContext):
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


# ==========================================
# ЗАВАНТАЖЕННЯ MP3
# ==========================================

async def save_mp3(
    file_id: str,
    filename: str,
    message: Message,
    state: FSMContext,
):
    temp_dir = Path(
        tempfile.mkdtemp(prefix="music_cover_bot_")
    )

    filename = Path(filename.replace("\\", "/")).name

    mp3_path = temp_dir / filename

    try:
        await message.answer("⏳ Завантажую MP3...")

        await download_telegram_file(
            message.bot,
            file_id,
            mp3_path,
        )

        if not check_mp3(mp3_path):
            shutil.rmtree(temp_dir, ignore_errors=True)

            await message.answer(
                "❌ Не вдалося прочитати цей MP3-файл."
            )
            return

        await state.update_data(
            temp_dir=str(temp_dir),
            mp3_path=str(mp3_path),
            filename=filename,
        )

        await message.answer(
            "✅ <b>MP3 отримано!</b>\n\n"
            "🖼 Тепер надішли фотографію, "
            "яку потрібно поставити на обкладинку."
        )

        await state.set_state(MusicState.waiting_for_cover)

    except Exception:
        logger.exception("Помилка під час завантаження MP3")

        shutil.rmtree(temp_dir, ignore_errors=True)

        await message.answer(
            "❌ Сталася помилка під час завантаження MP3."
        )


# ==========================================
# ОТРИМАННЯ ФОТОГРАФІЇ
# ==========================================

@router.message(MusicState.waiting_for_cover, F.photo)
async def receive_cover_photo(message: Message, state: FSMContext):
    if not message.photo:
        return

    photo = message.photo[-1]

    data = await state.get_data()

    temp_dir = Path(data["temp_dir"])

    cover_path = temp_dir / "cover.jpg"

    try:
        await message.answer(
            "⏳ Вбудовую фотографію в MP3..."
        )

        await download_telegram_file(
            message.bot,
            photo.file_id,
            cover_path,
        )

        await finish(
            message=message,
            state=state,
            cover_path=cover_path,
        )

    except Exception:
        logger.exception("Помилка під час обробки фото")

        await message.answer(
            "❌ Не вдалося обробити фотографію."
        )


# ==========================================
# ОТРИМАННЯ ФОТО ЯК DOCUMENT
# ==========================================

@router.message(MusicState.waiting_for_cover, F.document)
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

    data = await state.get_data()

    temp_dir = Path(data["temp_dir"])

    extension = Path(filename).suffix.lower()

    cover_path = temp_dir / f"cover{extension}"

    try:
        await message.answer(
            "⏳ Вбудовую фотографію в MP3..."
        )

        await download_telegram_file(
            message.bot,
            document.file_id,
            cover_path,
        )

        await finish(
            message=message,
            state=state,
            cover_path=cover_path,
        )

    except Exception:
        logger.exception(
            "Помилка під час обробки обкладинки"
        )

        await message.answer(
            "❌ Не вдалося обробити фотографію."
        )


# ==========================================
# ОБРОБКА ТА ВІДПРАВЛЕННЯ MP3
# ==========================================

async def finish(
    message: Message,
    state: FSMContext,
    cover_path: Path,
):
    data = await state.get_data()

    temp_dir = Path(data["temp_dir"])
    mp3_path = Path(data["mp3_path"])

    filename = data["filename"]

    try:
        # Замінюємо виключно обкладинку.
        replace_cover(
            mp3_path,
            cover_path,
        )

        logger.info(
            "Обкладинку успішно замінено: %s",
            mp3_path,
        )

        await message.answer(
            "📤 Готово! Надсилаю MP3..."
        )

        # Зберігаємо початкову назву файлу.
        await message.answer_audio(
            audio=FSInputFile(
                mp3_path,
                filename=filename,
            ),
            thumbnail=FSInputFile(cover_path),
        )

    except Exception:
        logger.exception(
            "Помилка під час обробки MP3"
        )

        await message.answer(
            "❌ Не вдалося додати обкладинку до цього MP3."
        )

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        await state.clear()

        await message.answer(
            "🔄 Для наступного треку надішли /start."
        )


# ==========================================
# ПОВІДОМЛЕННЯ ПРО НЕПРАВИЛЬНИЙ ФАЙЛ
# ==========================================

@router.message(MusicState.waiting_for_mp3)
async def wrong_mp3(message: Message):
    await message.answer(
        "🎵 Я очікую MP3-файл.\n\n"
        "Надішли його як аудіо або документ."
    )


@router.message(MusicState.waiting_for_cover)
async def wrong_cover(message: Message):
    await message.answer(
        "🖼 Я очікую фотографію.\n\n"
        "Надішли її як фото або JPG/PNG-файл."
    )
