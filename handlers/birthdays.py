# handlers/birthdays.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from states import BirthdayState, EditBirthdayState
from services.birthdays import (
    add_birthday_to_db,
    get_birthdays_by_manager,
    update_birthday_in_db,
    delete_birthday_from_db
)

router = Router()

# Крок 1: Початок додавання (Ім'я)
@router.message(Command("add_bd"))
async def cmd_add_birthday(message: Message, state: FSMContext):
    await message.answer("Введіть **ім'я** людини (наприклад: *Олександр*):")
    await state.set_state(BirthdayState.waiting_for_name)

@router.message(BirthdayState.waiting_for_name)
async def process_birthday_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        "Тепер введіть **Telegram-нікнейм** конкретної людини (з собачкою або без, наприклад: *@username*).\n"
        "Якщо нікнейма немає, просто напишіть прочерк: `-`"
    )
    await state.set_state(BirthdayState.waiting_for_username)

# Крок 2: Нікнейм людини
@router.message(BirthdayState.waiting_for_username)
async def process_birthday_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")
    await state.update_data(username=username)
    await message.answer("Тепер введіть дату народження у форматі **ДД.ММ** (наприклад: *10.11*):")
    await state.set_state(BirthdayState.waiting_for_date)

# Крок 3: Дата народження
@router.message(BirthdayState.waiting_for_date)
async def process_birthday_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    
    if len(date_text) != 5 or date_text[2] != '.':
        await message.answer("❌ Невірний формат. Введіть дату у форматі **ДД.ММ** (наприклад, 10.11):")
        return

    data = await state.get_data()
    name = data.get("name")
    username = data.get("username")
    manager_id = message.from_user.id
    
    await add_birthday_to_db(manager_id, name, username, date_text)
    await state.clear()
    
    person_display = f"@{username}" if username != "-" else "без нікнейма"
    await message.answer(
        f"✅ Успішно збережено!\n"
        f"👤 Людина: **{name}** ({person_display})\n"
        f"📅 Дата: **{date_text}**\n\n"
        f"Я надішлю вам сповіщення за день до цієї події о 09:00 ранку."
    )

# Перегляд списку конкретних людей
@router.message(Command("birthdays"))
async def cmd_list_birthdays(message: Message):
    manager_id = message.from_user.id
    records = await get_birthdays_by_manager(manager_id)
    
    if not records:
        await message.answer("📭 У вас поки немає збережених днів народження. Додайте їх за допомогою /add_bd")
        return
        
    text = "📋 **Дні народження конкретних людей:**\n\n"
    keyboard_buttons = []
    
    for rec_id, name, username, bdate in records:
        user_str = f" (@{username})" if username and username != "-" else ""
        text += f"• **{name}**{user_str} — {bdate}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"✏️ {name}", callback_data=f"edit_{rec_id}"),
            InlineKeyboardButton(text=f"❌ Видалити {name}", callback_data=f"del_{rec_id}")
        ])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(text, reply_markup=keyboard)

# Видалення
@router.callback_query(F.data.startswith("del_"))
async def process_delete_birthday(callback: CallbackQuery):
    record_id = int(callback.data.split("_")[1])
    manager_id = callback.from_user.id
    
    await delete_birthday_from_db(record_id, manager_id)
    await callback.answer("✅ Запис успішно видалено!", show_alert=True)
    
    try:
        await callback.message.edit_text("🗑 Запис видалено. Використайте /birthdays для перегляду актуального списку.")
    except Exception:
        pass

# Редагування: Крок 1 (Нове ім'я)
@router.callback_query(F.data.startswith("edit_"))
async def process_start_edit(callback: CallbackQuery, state: FSMContext):
    record_id = int(callback.data.split("_")[1])
    await state.update_data(edit_record_id=record_id)
    
    await callback.message.answer("✏️ Введіть **нове ім'я** для цієї людини:")
    await state.set_state(EditBirthdayState.waiting_for_new_name)
    await callback.answer()

@router.message(EditBirthdayState.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    await state.update_data(new_name=message.text.strip())
    await message.answer("Введіть **новий Telegram-нікнейм** (або `-`, якщо його немає):")
    await state.set_state(EditBirthdayState.waiting_for_new_username)

@router.message(EditBirthdayState.waiting_for_new_username)
async def process_new_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")
    await state.update_data(new_username=username)
    await message.answer("Тепер введіть **нову дату** народження у форматі **ДД.ММ** (наприклад: *15.06*):")
    await state.set_state(EditBirthdayState.waiting_for_new_date)

@router.message(EditBirthdayState.waiting_for_new_date)
async def process_new_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    
    if len(date_text) != 5 or date_text[2] != '.':
        await message.answer("❌ Невірний формат. Введіть дату у форматі **ДД.ММ** (наприклад, 15.06):")
        return

    data = await state.get_data()
    record_id = data.get("edit_record_id")
    new_name = data.get("new_name")
    new_username = data.get("new_username")
    manager_id = message.from_user.id
    
    await update_birthday_in_db(record_id, manager_id, new_name, new_username, date_text)
    await state.clear()
    
    user_display = f"@{new_username}" if new_username != "-" else "без нікнейма"
    await message.answer(f"✅ Дані успішно оновлено!\n👤 Людина: **{new_name}** ({user_display})\n📅 Дата: **{date_text}**")