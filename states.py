from aiogram.fsm.state import State, StatesGroup

class MusicState(StatesGroup):
    waiting_for_mp3 = State()
    waiting_for_cover = State()

class BirthdayState(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()