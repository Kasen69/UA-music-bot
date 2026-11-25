from html import escape
from aiogram import Bot
from config import COMMUNITY_CHAT_ID, TEAM_USERNAMES


async def get_team_mentions(bot: Bot) -> list[str]:
    mentions: list[str] = []

    # 1. Якщо юзернейми задані вручну в config.py
    if TEAM_USERNAMES:
        for raw in TEAM_USERNAMES:
            username = raw.strip().lstrip("@")
            # Пропускаємо порожні рядки та ботів
            if not username or username.lower().endswith("bot"):
                continue
            mentions.append(f"@{escape(username)}")
        return mentions

    # 2. Якщо TEAM_USERNAMES порожній — тягнемо адмінів спільноти та відсіюємо ботів
    admins = await bot.get_chat_administrators(COMMUNITY_CHAT_ID)
    for member in admins:
        user = member.user
        if user.is_bot:
            continue
        if user.username:
            mentions.append(f"@{escape(user.username)}")
        else:
            # Фолбек, якщо в учасника не встановлений @username
            mentions.append(f'<a href="tg://user?id={user.id}">{escape(user.first_name)}</a>')

    return mentions


def build_announcement_messages(
    text: str,
    mentions: list[str],
    chunk_size: int = 5,
) -> list[str]:
    chunks = [mentions[i : i + chunk_size] for i in range(0, len(mentions), chunk_size)]

    # Перше повідомлення: сам текст оголошення + перші 5 людей
    messages = [f"{escape(text)}\n\n{' '.join(chunks[0])}"]

    # Наступні повідомлення (якщо в команді > 5 людей): по 5 тегів у кожному
    for extra_chunk in chunks[1:]:
        messages.append(" ".join(extra_chunk))

    return messages