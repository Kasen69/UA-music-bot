import os
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу (корисно для локальної розробки)
load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

if not TOKEN:
    raise ValueError("TOKEN не знайдено у змінних середовища!")