import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', 'uaoldmusic').lstrip('@').lower()
if not BOT_TOKEN:
    raise ValueError('BOT_TOKEN не знайдено у .env')
