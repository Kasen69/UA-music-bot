import os

TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

if not TOKEN:
    raise ValueError("TOKEN не знайдено у змінних середовища!")
