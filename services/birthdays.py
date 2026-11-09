# services/birthdays.py
from datetime import datetime, timedelta
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

DB_PATH = "birthdays.db"

async def init_birthday_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS birthdays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                birth_date TEXT NOT NULL
            )
        """)
        await db.commit()

async def add_birthday_to_db(manager_id: int, name: str, birth_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO birthdays (manager_id, name, birth_date) VALUES (?, ?, ?)",
            (manager_id, name, birth_date)
        )
        await db.commit()

# Функція перевірки (спрацьовує щодня о 09:00 ранку)
async def check_upcoming_birthdays(bot: Bot):
    tomorrow = datetime.now() + timedelta(days=1)
    target_date = tomorrow.strftime("%d.%m") # Формат ДД.ММ
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT manager_id, name FROM birthdays WHERE birth_date = ?", (target_date,)
        ) as cursor:
            records = await cursor.fetchall()
            
    # Групуємо сповіщення по менеджерах
    notifications = {}
    for manager_id, name in records:
        if manager_id not in notifications:
            notifications[manager_id] = []
        notifications[manager_id].append(name)
        
    # Розсилаємо сповіщення кожному відповідальному
    for manager_id, names in notifications.items():
        names_str = ", ".join(names)
        try:
            await bot.send_message(
                manager_id,
                f"🔔 **Нагадування про дні народження!**\n\nЗавтра ({target_date}) свято у: **{names_str}**! 🎂 Не забудьте привітати."
            )
        except Exception as e:
            print(f"Не вдалося надіслати сповіщення для менеджера {manager_id}: {e}")

def setup_birthday_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(check_upcoming_birthdays, 'cron', hour=9, minute=0, args=[bot])
    scheduler.start()