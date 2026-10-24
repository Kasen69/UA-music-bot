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
from services.music import is_mp3, is_image, check_mp3, replace_cover

logger = logging.getLogger(__name__)
router = Router(name='music')

@router.message(Command('start'))
async def start_command(message: Message, state: FSMContext):
    """
    Запускає процес.
    """
    data = await state.get_data()
    old_temp_dir = data.get('temp_dir')
    if old_temp_dir:
        shutil.rmtree(old_temp_dir, ignore_errors=True)
    await state.clear()
    await message.answer('🎵 <b>Music Cover Bot</b>\n\nНадішли мені MP3-файл.\n\nПісля цього я попрошу фотографію, яку потрібно поставити на обкладинку.')
    await state.set_state(MusicState.waiting_for_mp3)

@router.message(Command('cancel'))
async def cancel_command(message: Message, state: FSMContext):
    """
    Скасовує поточну операцію.
    """
    data = await state.get_data()
    temp_dir = data.get('temp_dir')
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)
    await state.clear()
    await message.answer('❌ Операцію скасовано.\n\nДля нового треку натисни /start.')

@router.message(MusicState.waiting_for_mp3, F.audio)
async def receive_mp3_audio(message: Message, state: FSMContext):
    """
    Отримує MP3, відправлений
    як звичайне Telegram Audio.
    """
    audio = message.audio
    if not audio:
        return
    filename = audio.file_name or 'music.mp3'
    if not is_mp3(filename):
        await message.answer('❌ Потрібен саме MP3-файл.')
        return
    await save_mp3(file_id=audio.file_id, filename=filename, message=message, state=state)

@router.message(MusicState.waiting_for_mp3, F.document)
async def receive_mp3_document(message: Message, state: FSMContext):
    """
    Отримує MP3, відправлений
    як Telegram Document.
    """
    document = message.document
    if not document:
        return
    filename = document.file_name or ''
    if not is_mp3(filename):
        await message.answer('❌ Потрібен саме MP3-файл.')
        return
    await save_mp3(file_id=document.file_id, filename=filename, message=message, state=state)

async def save_mp3(file_id: str, filename: str, message: Message, state: FSMContext):
    """
    Завантажує MP3 та переводить
    бота в режим очікування фото.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix='music_cover_bot_'))
    filename = Path(filename.replace("\\", "/")).name
    mp3_path = temp_dir / filename
    try:
        await message.answer('⏳ Завантажую MP3...')
        await download_telegram_file(message.bot, file_id, mp3_path)
        if not check_mp3(mp3_path):
            shutil.rmtree(temp_dir, ignore_errors=True)
            await message.answer('❌ Не вдалося прочитати цей MP3-файл.')
            return
        await state.update_data(temp_dir=str(temp_dir), mp3_path=str(mp3_path), filename=filename)
        await message.answer('✅ <b>MP3 отримано!</b>\n\n🖼 Тепер надішли фотографію, яку потрібно поставити на обкладинку.')
        await state.set_state(MusicState.waiting_for_cover)
    except Exception:
        logger.exception('Помилка під час завантаження MP3')
        shutil.rmtree(temp_dir, ignore_errors=True)
        await message.answer('❌ Сталася помилка під час завантаження MP3.')

@router.message(MusicState.waiting_for_cover, F.photo)
async def receive_cover_photo(message: Message, state: FSMContext):
    """
    Отримує звичайне Telegram-фото.
    """
    if not message.photo:
        return
    photo = message.photo[-1]
    data = await state.get_data()
    temp_dir = Path(data['temp_dir'])
    cover_path = temp_dir / 'cover.jpg'
    try:
        await message.answer('⏳ Вбудовую фотографію в MP3...')
        await download_telegram_file(message.bot, photo.file_id, cover_path)
        await finish(message=message, state=state, cover_path=cover_path)
    except Exception:
        logger.exception('Помилка під час обробки фото')
        await message.answer('❌ Не вдалося обробити фотографію.')

@router.message(MusicState.waiting_for_cover, F.document)
async def receive_cover_document(message: Message, state: FSMContext):
    """
    Отримує JPG / JPEG / PNG,
    відправлений як файл.
    """
    document = message.document
    if not document:
        return
    filename = document.file_name or ''
    if not is_image(filename):
        await message.answer('❌ Надішли фотографію або JPG/PNG-файл.')
        return
    data = await state.get_data()
    temp_dir = Path(data['temp_dir'])
    extension = Path(filename).suffix.lower()
    cover_path = temp_dir / f'cover{extension}'
    try:
        await message.answer('⏳ Вбудовую фотографію в MP3...')
        await download_telegram_file(message.bot, document.file_id, cover_path)
        await finish(message=message, state=state, cover_path=cover_path)
    except Exception:
        logger.exception('Помилка під час обробки обкладинки')
        await message.answer('❌ Не вдалося обробити фотографію.')

async def finish(message: Message, state: FSMContext, cover_path: Path):
    """
    Вбудовує обкладинку в MP3
    та повертає файл користувачу.
    """
    data = await state.get_data()
    temp_dir = Path(data['temp_dir'])
    mp3_path = Path(data['mp3_path'])
    try:
        replace_cover(mp3_path, cover_path)
        logger.info('Обкладинку успішно додано: %s', mp3_path)
        await message.answer('📤 Готово! Надсилаю MP3...')
        telegram_filename = mp3_path.stem
        await message.answer_audio(audio=FSInputFile(mp3_path, filename=telegram_filename), thumbnail=FSInputFile(cover_path))
    except Exception as e:
        logger.exception('Помилка під час обробки MP3: %s', e)
        await message.answer('❌ Не вдалося додати обкладинку до цього MP3.')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        await state.clear()
        await message.answer('🔄 Для наступного треку надішли /start.')

@router.message(MusicState.waiting_for_mp3)
async def wrong_mp3(message: Message):
    await message.answer('🎵 Я очікую MP3-файл.\n\nНадішли його як аудіо або документ.')

@router.message(MusicState.waiting_for_cover)
async def wrong_cover(message: Message):
    await message.answer('🖼 Я очікую фотографію.\n\nНадішли її як фото або JPG/PNG-файл.')
