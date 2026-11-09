# handlers/birthdays.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states import BirthdayState
from services.birthdays import add_birthday_to_db

router = Router()

@router.message(Command("add_bd"))
async def cmd_add_birthday(message: Message, state: FSMContext):
    # Кожна людина, яка пише цю команду, стає менеджером свого списку
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
    manager_id = message.from_user.id  # Фіксуємо унікальний ID користувача, що додав запис
    
    await add_birthday_to_db(manager_id, name, date_text)
    await state.clear()
    
    await message.answer(
        f"✅ Успішно збережено!\n"
        f"Ім'я: **{name}**\n"
        f"Дата: **{date_text}**\n\n"
        f"Я надішлю вам особисте сповіщення за день до цієї події о 09:00 ранку."
    )