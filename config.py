import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Отримання токена з Environment Variables або .env
BOT_TOKEN = os.getenv("TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")

# Налаштування каналу
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")

# Налаштування Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
STORAGE_FILE = BASE_DIR / "posts.json"


def check_bot_token():
    if not BOT_TOKEN:
        raise ValueError("TOKEN (або TELEGRAM_BOT_TOKEN) не знайдено у змінних середовища чи у файлі .env!")
