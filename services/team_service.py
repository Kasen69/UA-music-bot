from html import escape
from aiogram import Bot
from config import COMMUNITY_CHAT_ID, TEAM_USERNAMES


async def get_team_mentions(bot: Bot) -> list[str]:
    mentions: list[str] = []

    if TEAM_USERNAMES:
        for raw in TEAM_USERNAMES:
            # Прибираємо @ і випадкові пробіли до/після символу
            username = raw.replace("@", "").strip()
            if not username or username.lower().endswith("bot"):
                continue
            mentions.append(f"@{escape(username)}")
        return mentions

    admins = await bot.get_chat_administrators(COMMUNITY_CHAT_ID)
    for member in admins:
        user = member.user
        if user.is_bot:
            continue
        if user.username:
            mentions.append(f"@{escape(user.username)}")
        else:
            mentions.append(f'<a href="tg://user?id={user.id}">{escape(user.first_name)}</a>')

    return mentions


def build_announcement_messages(
    text: str,
    mentions: list[str],
    chunk_size: int = 5,
) -> list[str]:
    # 1. Перше повідомлення — виключно сам текст оголошення
    messages = [escape(text)]

    # 2. Наступні повідомлення — тільки теги, розбиті по 5 людей
    chunks = [mentions[i : i + chunk_size] for i in range(0, len(mentions), chunk_size)]
    for chunk in chunks:
        messages.append(" ".join(chunk))

    return messages