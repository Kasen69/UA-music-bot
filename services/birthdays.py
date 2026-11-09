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
                username TEXT,
                birth_date TEXT NOT NULL
            )
        """)
        await db.commit()

async def add_birthday_to_db(manager_id: int, name: str, username: str, birth_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO birthdays (manager_id, name, username, birth_date) VALUES (?, ?, ?, ?)",
            (manager_id, name, username, birth_date)
        )
        await db.commit()

async def get_birthdays_by_manager(manager_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, name, username, birth_date FROM birthdays WHERE manager_id = ?", (manager_id,)
        ) as cursor:
            return await cursor.fetchall()

async def update_birthday_in_db(record_id: int, manager_id: int, name: str, username: str, birth_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE birthdays SET name = ?, username = ?, birth_date = ? WHERE id = ? AND manager_id = ?",
            (name, username, birth_date, record_id, manager_id)
        )
        await db.commit()

async def delete_birthday_from_db(record_id: int, manager_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM birthdays WHERE id = ? AND manager_id = ?",
            (record_id, manager_id)
        )
        await db.commit()

# Щоденна перевірка (тепер із виведенням нікнейма людини)
async def check_upcoming_birthdays(bot: Bot):
    tomorrow = datetime.now() + timedelta(days=1)
    target_date = tomorrow.strftime("%d.%m")
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT manager_id, name, username FROM birthdays WHERE birth_date = ?", (target_date,)
        ) as cursor:
            records = await cursor.fetchall()
            
    notifications = {}
    for manager_id, name, username in records:
        if manager_id not in notifications:
            notifications[manager_id] = []
        
        # Формуємо красиве згадування людини
        person_str = f"**{name}** (@{username})" if username and username != "-" else f"**{name}**"
        notifications[manager_id].append(person_str)
        
    for manager_id, people in notifications.items():
        people_str = ", ".join(people)
        try:
            await bot.send_message(
                manager_id,
                f"🔔 **Нагадування про дні народження!**\n\nЗавтра ({target_date}) свято у: {people_str}! 🎂 Не забудьте привітати."
            )
        except Exception as e:
            print(f"Не вдалося надіслати сповіщення для менеджера {manager_id}: {e}")

def setup_birthday_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(check_upcoming_birthdays, 'cron', hour=9, minute=0, args=[bot])
    scheduler.start()