"""Application configuration loaded from environment."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory (root of UA Music)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TOKEN", "")

# Default Gemini model
# Recommended: 'gemini-3.5-flash-lite' (fast & efficient) or 'gemini-3.8-flash' (deep multimodal reasoning)
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Storage file path
STORAGE_FILE = BASE_DIR / "posts.json"
