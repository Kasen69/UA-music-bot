
import os

# Отримання токена з Environment Variables хостингу
BOT_TOKEN = os.getenv("TOKEN")

# Налаштування каналу
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")

if not BOT_TOKEN:
    raise ValueError("TOKEN не знайдено у змінних середовища!")

