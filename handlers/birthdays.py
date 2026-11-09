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

# Початок додавання дня народження
@router.message(Command("add_bd"))
async def cmd_add_birthday(message: Message, state: FSMContext):
    await message.answer("Введіть **ім'я** іменинника (наприклад: *Олександр*):")
    await state.set_state(BirthdayState.waiting_for_name)

@router.message(BirthdayState.waiting_for_name)
async def process_birthday_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Тепер введіть дату народження у форматі **ДД.ММ** (наприклад: *10.11*):")
    await state.set_state(BirthdayState.waiting_for_date)

@router.message(BirthdayState.waiting_for_date)
async def process_birthday_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    
    if len(date_text) != 5 or date_text[2] != '.':
        await message.answer("❌ Невірний формат. Будь ласка, введіть дату у форматі **ДД.ММ** (наприклад, 10.11):")
        return

    data = await state.get_data()
    name = data.get("name")
    manager_id = message.from_user.id
    
    await add_birthday_to_db(manager_id, name, date_text)
    await state.clear()
    
    await message.answer(
        f"✅ Успішно збережено!\n"
        f"Ім'я: **{name}**\n"
        f"Дата: **{date_text}**\n\n"
        f"Я надішлю вам особисте сповіщення за день до цієї події о 09:00 ранку."
    )

# Перегляд списку днів народження з інлайн-кнопками управління
@router.message(Command("birthdays"))
async def cmd_list_birthdays(message: Message):
    manager_id = message.from_user.id
    records = await get_birthdays_by_manager(manager_id)
    
    if not records:
        await message.answer("📭 У вас поки немає збережених днів народження. Додайте їх за допомогою /add_bd")
        return
        
    text = "📋 **Ваші збережені дні народження:**\n\n"
    keyboard_buttons = []
    
    for rec_id, name, bdate in records:
        text += f"• **{name}** — {bdate}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"✏️ Редагувати: {name}", callback_data=f"edit_{rec_id}"),
            InlineKeyboardButton(text=f"❌ Видалити", callback_data=f"del_{rec_id}")
        ])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(text, reply_markup=keyboard)

# Видалення запису
@router.callback_query(F.data.startswith("del_"))
async def process_delete_birthday(callback: CallbackQuery):
    record_id = int(callback.data.split("_")[1])
    manager_id = callback.from_user.id
    
    await delete_birthday_from_db(record_id, manager_id)
    await callback.answer("✅ Запис успішно видалено!", show_alert=True)
    
    try:
        await callback.message.edit_text("🗑 Запис видалено. Використайте /birthdays, щоб переглянути оновлений список.")
    except Exception:
        pass

# Початок редагування запису
@router.callback_query(F.data.startswith("edit_"))
async def process_start_edit(callback: CallbackQuery, state: FSMContext):
    record_id = int(callback.data.split("_")[1])
    
    await state.update_data(edit_record_id=record_id)
    
    await callback.message.answer("✏️ Введіть **нове ім'я** для цього іменинника:")
    await state.set_state(EditBirthdayState.waiting_for_new_name)
    await callback.answer()

@router.message(EditBirthdayState.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    await state.update_data(new_name=message.text.strip())
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
    manager_id = message.from_user.id
    
    await update_birthday_in_db(record_id, manager_id, new_name, date_text)
    await state.clear()
    
    await message.answer(f"✅ Дані успішно оновлено!\nІм'я: **{new_name}**\nДата: **{date_text}**")