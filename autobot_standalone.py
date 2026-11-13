"""
Telegram-бот для генерації постів про пісні та зображення на базі Gemini AI.
Підтримує аналіз треків з YouTube, зображень, рецензування, редагування та збереження в JSON.
Всі запити та відповіді моделі генеруються виключно українською мовою.
"""

import os
import sys
import tempfile
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from core.config import TELEGRAM_BOT_TOKEN
from core.models import PostStatus
from services.post_generator import PostGeneratorService

# Ініціалізація спільного сервісу генерації
service = PostGeneratorService()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Надсилає привітання та інструкцію користування."""
    msg = (
        "👋 *Вітаємо у Gemini Music & Content Bot!*\n\n"
        "Я створюю атмосферні огляди та пости про музичні треки (з YouTube або за назвою), "
        "аналізую обкладинки/зображення та допомагаю рецензувати, редагувати й зберігати їх у файл `.json`.\n\n"
        "🎵 *Команди для музики:*\n"
        "• `/song <YouTube посилання або назва треку>` — згенерувати пост українською мовою\n\n"
        "🖼️ *Робота із зображеннями:*\n"
        "• Просто надішліть будь-яке фото чи обкладинку (можна додати опис або побажання в підписі)!\n\n"
        "📋 *Керування та рецензування:*\n"
        "• `/posts` — переглянути список збережених постів у базі\n"
        "• `/review <id>` — переглянути повний текст поста та його статус\n"
        "• `/edit <id> <новий текст>` — відредагувати текст поста\n"
        "• `/approve <id>` — затвердити пост (перевести в статус APPROVED)\n"
        "• `/delete <id>` — видалити пост з бази\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def song_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє команду /song <посилання або назва>."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Будь ласка, вкажіть YouTube посилання або назву пісні.\n"
            "Приклад: `/song https://www.youtube.com/watch?v=...`\n"
            "або: `/song Океан Ельзи Без бою`",
            parse_mode="Markdown",
        )
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text("⏳ *Отримую дані та генерую пост українською мовою через Gemini AI...*", parse_mode="Markdown")

    try:
        post = service.create_post_from_song(query)
        tags = " ".join(post.hashtags) if post.hashtags else ""

        reply_text = (
            f"✅ *Пост згенеровано та збережено в posts.json!*\n"
            f"🆔 *ID:* `{post.id}`\n"
            f"📌 *Статус:* `[{post.status.value.upper()}]`\n"
            f"🏷️ *Заголовок:* *{post.title}*\n\n"
            f"{post.content}\n\n"
            f"{tags}\n\n"
            f"✏️ *Щоб змінити текст:* `/edit {post.id} <ваш новий текст>`\n"
            f"👍 *Щоб затвердити:* `/approve {post.id}`"
        )
        await status_msg.edit_text(reply_text, parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"❌ *Помилка генерації поста:* {str(e)}", parse_mode="Markdown")


async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє завантажені фото, аналізує через Gemini та створює пост українською."""
    photo = update.message.photo[-1]  # Найвища роздільна здатність
    caption = update.message.caption or ""

    status_msg = await update.message.reply_text("⏳ *Завантажую фото та аналізую через Gemini AI українською мовою...*", parse_mode="Markdown")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "incoming_image.jpg"
        file = await photo.get_file()
        await file.download_to_drive(str(tmp_path))

        try:
            post = service.create_post_from_image(
                image_path=str(tmp_path),
                custom_instructions=caption if caption else None,
            )
            tags = " ".join(post.hashtags) if post.hashtags else ""

            reply_text = (
                f"✅ *Зображення проаналізовано! Пост збережено в JSON!*\n"
                f"🆔 *ID:* `{post.id}`\n"
                f"📌 *Статус:* `[{post.status.value.upper()}]`\n"
                f"🏷️ *Заголовок:* *{post.title}*\n\n"
                f"{post.content}\n\n"
                f"{tags}\n\n"
                f"✏️ *Щоб змінити текст:* `/edit {post.id} <ваш новий текст>`\n"
                f"👍 *Щоб затвердити:* `/approve {post.id}`"
            )
            await status_msg.edit_text(reply_text, parse_mode="Markdown")
        except Exception as e:
            await status_msg.edit_text(f"❌ *Помилка аналізу зображення:* {str(e)}", parse_mode="Markdown")


async def list_posts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує список останніх збережених постів."""
    posts = service.get_all_posts()
    if not posts:
        await update.message.reply_text("📂 У базі `posts.json` поки немає збережених постів.", parse_mode="Markdown")
        return

    lines = ["📋 *Останні збережені пости:*\n"]
    for p in posts[:8]:
        lines.append(f"• `[{p.status.value.upper()}]` `{p.id}`: *{p.title}*")

    lines.append("\n_Використовуйте `/review <id>` для перегляду тексту._")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує деталі конкретного поста."""
    if not context.args:
        await update.message.reply_text("⚠️ Вкажіть ID поста: `/review <post_id>`", parse_mode="Markdown")
        return

    post_id = context.args[0].strip()
    post = service.get_post(post_id)
    if not post:
        await update.message.reply_text(f"❌ Пост з ID `{post_id}` не знайдено.", parse_mode="Markdown")
        return

    tags = " ".join(post.hashtags) if post.hashtags else ""
    text = (
        f"🔍 *Рецензування поста:*\n"
        f"🆔 *ID:* `{post.id}`\n"
        f"📌 *Статус:* `[{post.status.value.upper()}]`\n"
        f"🏷️ *Джерело:* `{post.source_type.value}`\n"
        f"📅 *Створено:* `{post.created_at[:19]}`\n\n"
        f"*{post.title}*\n\n"
        f"{post.content}\n\n"
        f"{tags}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редагує текст поста в JSON."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Формат команди: `/edit <post_id> <новий текст поста>`",
            parse_mode="Markdown",
        )
        return

    post_id = context.args[0]
    new_text = " ".join(context.args[1:])

    updated = service.edit_post(post_id, new_content=new_text, new_status=PostStatus.REVIEWED)
    if not updated:
        await update.message.reply_text(f"❌ Пост `{post_id}` не знайдено.", parse_mode="Markdown")
        return

    await update.message.reply_text(
        f"✅ *Текст поста `{post_id}` успішно оновлено та збережено в JSON!*",
        parse_mode="Markdown",
    )


async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Затверджує пост."""
    if not context.args:
        await update.message.reply_text("⚠️ Формат команди: `/approve <post_id>`", parse_mode="Markdown")
        return

    post_id = context.args[0]
    updated = service.approve_post(post_id)
    if not updated:
        await update.message.reply_text(f"❌ Пост `{post_id}` не знайдено.", parse_mode="Markdown")
        return

    await update.message.reply_text(f"🎉 *Пост `{post_id}` успішно затверджено (APPROVED)!*", parse_mode="Markdown")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Видаляє пост з бази."""
    if not context.args:
        await update.message.reply_text("⚠️ Формат команди: `/delete <post_id>`", parse_mode="Markdown")
        return

    post_id = context.args[0]
    if service.delete_post(post_id):
        await update.message.reply_text(f"🗑️ *Пост `{post_id}` видалено з posts.json.*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Пост `{post_id}` не знайдено.", parse_mode="Markdown")


def main():
    token = TELEGRAM_BOT_TOKEN
    if not token or token == "your_telegram_bot_token_here":
        print("=" * 60)
        print("⚠️  TELEGRAM_BOT_TOKEN не налаштовано!")
        print("=" * 60)
        print("1. Відкрийте Telegram та знайдіть бота @BotFather")
        print("2. Надішліть команду /newbot і скопіюйте отриманий токен")
        print("3. Вставте його у файл .env:")
        print("   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz")
        print("4. Після цього запустіть: python bot.py")
        print("=" * 60)
        sys.exit(1)

    print("🤖 Запуск Telegram-бота...")
    app = ApplicationBuilder().token(token).build()

    # Обробники команд
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("song", song_command))
    app.add_handler(CommandHandler("posts", list_posts_command))
    app.add_handler(CommandHandler("review", review_command))
    app.add_handler(CommandHandler("edit", edit_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("delete", delete_command))

    # Обробник зображень
    app.add_handler(MessageHandler(filters.PHOTO, image_handler))

    print("✅ Бот онлайн та очікує повідомлень! Натисніть Ctrl+C для зупинки.")
    app.run_polling()


if __name__ == "__main__":
    main()
