"""
Aiogram 3 роутер для генерації та рецензування постів про пісні та зображення на базі Gemini AI.
Підтримує YouTube, огляд обкладинок/фотографій, керування базою posts.json.
"""

import asyncio
import html
import logging
import os
import tempfile
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import Message

from core.models import PostStatus
from services.post_generator import PostGeneratorService
from services.memory import free_memory

logger = logging.getLogger(__name__)
router = Router(name="autobot")

_service: PostGeneratorService | None = None


def get_service() -> PostGeneratorService:
    global _service
    if _service is None:
        _service = PostGeneratorService()
    return _service


@router.message(Command("help"))
async def help_command(message: Message):
    """Показує список доступних команд."""
    text = (
        "🤖 <b>Команди помічника UA Music & Gemini AI:</b>\n\n"
        "🎵 <b>Генерація постів про музику:</b>\n"
        "• <code>/song &lt;посилання на YouTube або назва треку&gt;</code> — "
        "створити атмосферний огляд/пост українською мовою\n\n"
        "🖼 <b>Аналіз зображень:</b>\n"
        "• Просто надішліть будь-яке <b>фото чи обкладинку</b> (можна з підписом чи побажаннями) "
        "для створення посту\n\n"
        "📋 <b>Керування та рецензування постів:</b>\n"
        "• <code>/posts</code> — переглянути останні збережені пости\n"
        "• <code>/review &lt;id&gt;</code> — переглянути повний текст посту\n"
        "• <code>/edit &lt;id&gt; &lt;новий текст&gt;</code> — змінити текст посту\n"
        "• <code>/approve &lt;id&gt;</code> — затвердити пост (статус APPROVED)\n"
        "• <code>/delete &lt;id&gt;</code> — видалити пост із бази\n\n"
        "🎧 <b>Робота з аудіо:</b>\n"
        "• Надішліть <b>MP3</b> для зміни його обкладинки\n"
        "• <code>/cancel</code> — скинути поточний стан"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("song"))
async def song_command(message: Message, command: CommandObject):
    """Генерує пост за YouTube-посиланням або назвою пісні."""
    if not command.args:
        await message.answer(
            "⚠️ <b>Вкажіть посилання або назву пісні!</b>\n\n"
            "Приклад:\n"
            "• <code>/song https://www.youtube.com/watch?v=dQw4w9WgXcQ</code>\n"
            "• <code>/song Океан Ельзи - Обійми</code>",
            parse_mode="HTML",
        )
        return

    query = command.args.strip()
    status_msg = await message.answer(
        "🔍 <b>Шукаю інформацію про трек та генерую пост через Gemini AI...</b>\n"
        "<i>Це може зайняти кілька секунд.</i>",
        parse_mode="HTML",
    )

    try:
        service = get_service()
        post = await asyncio.to_thread(service.create_post_from_song, query)

        tags = " ".join(f"#{t.lstrip('#')}" for t in post.hashtags) if post.hashtags else ""
        escaped_title = html.escape(post.title or "Огляд пісні")
        escaped_content = html.escape(post.content or "")
        escaped_source = html.escape(post.source_ref or query)

        result_text = (
            f"✅ <b>Пост успішно згенеровано!</b>\n\n"
            f"🎵 <b>{escaped_title}</b>\n\n"
            f"{escaped_content}\n\n"
            f"{tags}\n\n"
            f"─────────────────────\n"
            f"🆔 <code>{post.id}</code> | Статус: <b>{post.status.value.upper()}</b>\n"
            f"🔗 Джерело: {escaped_source}"
        )

        await status_msg.edit_text(result_text, parse_mode="HTML")
    except Exception as e:
        logger.exception("Помилка генерації посту для: %s", query)
        await status_msg.edit_text(
            f"❌ <b>Помилка під час генерації:</b>\n<code>{html.escape(str(e))}</code>",
            parse_mode="HTML",
        )
    finally:
        free_memory()


@router.message(StateFilter(None), F.photo)
async def image_to_post_handler(message: Message):
    """Обробляє надіслане фото та створює пост через Gemini AI (якщо користувач не в процесі зміни обкладинки MP3)."""
    status_msg = await message.answer(
        "🎨 <b>Аналізую зображення через Gemini AI та створюю пост...</b>\n"
        "<i>Зачекайте декілька секунд.</i>",
        parse_mode="HTML",
    )

    photo = message.photo[-1]
    prompt = message.caption or "Створи атмосферний огляд цього зображення або обкладинки"

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)

        await message.bot.download(photo, destination=temp_path)

        service = get_service()
        post = await asyncio.to_thread(service.create_post_from_image, str(temp_path), prompt)

        tags = " ".join(f"#{t.lstrip('#')}" for t in post.hashtags) if post.hashtags else ""
        escaped_title = html.escape(post.title or "Огляд зображення")
        escaped_content = html.escape(post.content or "")

        result_text = (
            f"✅ <b>Пост за зображенням готовий!</b>\n\n"
            f"🖼 <b>{escaped_title}</b>\n\n"
            f"{escaped_content}\n\n"
            f"{tags}\n\n"
            f"─────────────────────\n"
            f"🆔 <code>{post.id}</code> | Статус: <b>{post.status.value.upper()}</b>"
        )

        await status_msg.edit_text(result_text, parse_mode="HTML")
    except Exception as e:
        logger.exception("Помилка обробки зображення")
        await status_msg.edit_text(
            f"❌ <b>Помилка аналізу зображення:</b>\n<code>{html.escape(str(e))}</code>",
            parse_mode="HTML",
        )
    finally:
        if temp_path and temp_path.exists():
            try:
                os.remove(temp_path)
            except OSError:
                pass
        free_memory()


@router.message(Command("posts"))
async def list_posts_command(message: Message):
    """Виводить список збережених постів."""
    try:
        service = get_service()
        posts = service.get_all_posts()
        if not posts:
            await message.answer(
                "📭 <b>У базі ще немає збережених постів.</b>\n"
                "Скористайтеся командою <code>/song</code> або надішліть фото для генерації.",
                parse_mode="HTML",
            )
            return

        lines = ["📋 <b>Останні збережені пости:</b>\n"]
        for p in reversed(posts[-10:]):
            clean_title = html.escape(p.title[:60])
            status_tag = p.status.value.upper()
            lines.append(f"• <b>{clean_title}</b>\n  🆔 <code>{p.id}</code> | [{status_tag}]\n")

        lines.append("\n<i>Щоб переглянути пост повністю:</i> <code>/review &lt;id&gt;</code>")
        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.exception("Помилка отримання постів")
        await message.answer(f"❌ <b>Помилка:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")


@router.message(Command("review"))
async def review_command(message: Message, command: CommandObject):
    """Показує повний текст поста за ID."""
    if not command.args:
        await message.answer("⚠️ Вкажіть ID поста: <code>/review &lt;post_id&gt;</code>", parse_mode="HTML")
        return

    post_id = command.args.strip()
    try:
        service = get_service()
        post = service.get_post(post_id)
        if not post:
            await message.answer(f"❌ Пост <code>{html.escape(post_id)}</code> не знайдено.", parse_mode="HTML")
            return

        tags = " ".join(f"#{t.lstrip('#')}" for t in post.hashtags) if post.hashtags else ""
        escaped_title = html.escape(post.title or "Без назви")
        escaped_content = html.escape(post.content or "")
        created = html.escape(post.created_at[:19].replace("T", " "))

        text = (
            f"📖 <b>Рецензія поста:</b> <code>{post.id}</code>\n"
            f"📌 Статус: <b>{post.status.value.upper()}</b> | 📅 {created}\n"
            f"─────────────────────\n\n"
            f"🎵 <b>{escaped_title}</b>\n\n"
            f"{escaped_content}\n\n"
            f"{tags}\n\n"
            f"─────────────────────\n"
            f"Команди: <code>/approve {post.id}</code> | <code>/delete {post.id}</code>"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.exception("Помилка рецензування поста")
        await message.answer(f"❌ <b>Помилка:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")


@router.message(Command("edit"))
async def edit_command(message: Message, command: CommandObject):
    """Редагує текст поста в JSON."""
    args = (command.args or "").split()
    if len(args) < 2:
        await message.answer(
            "⚠️ Формат команди: <code>/edit &lt;post_id&gt; &lt;новий текст поста&gt;</code>",
            parse_mode="HTML",
        )
        return

    post_id = args[0]
    new_text = " ".join(args[1:])

    try:
        service = get_service()
        updated = service.edit_post(post_id, new_content=new_text, new_status=PostStatus.REVIEWED)
        if not updated:
            await message.answer(f"❌ Пост <code>{html.escape(post_id)}</code> не знайдено.", parse_mode="HTML")
            return

        await message.answer(
            f"✅ <b>Текст поста <code>{html.escape(post_id)}</code> успішно оновлено!</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("Помилка редагування поста")
        await message.answer(f"❌ <b>Помилка:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")


@router.message(Command("approve"))
async def approve_command(message: Message, command: CommandObject):
    """Затверджує пост (APPROVED)."""
    if not command.args:
        await message.answer("⚠️ Формат команди: <code>/approve &lt;post_id&gt;</code>", parse_mode="HTML")
        return

    post_id = command.args.strip()
    try:
        service = get_service()
        updated = service.approve_post(post_id)
        if not updated:
            await message.answer(f"❌ Пост <code>{html.escape(post_id)}</code> не знайдено.", parse_mode="HTML")
            return

        await message.answer(
            f"🎉 <b>Пост <code>{html.escape(post_id)}</code> успішно затверджено (APPROVED)!</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("Помилка затвердження поста")
        await message.answer(f"❌ <b>Помилка:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")


@router.message(Command("delete"))
async def delete_command(message: Message, command: CommandObject):
    """Видаляє пост із бази."""
    if not command.args:
        await message.answer("⚠️ Формат команди: <code>/delete &lt;post_id&gt;</code>", parse_mode="HTML")
        return

    post_id = command.args.strip()
    try:
        service = get_service()
        if service.delete_post(post_id):
            await message.answer(
                f"🗑 <b>Пост <code>{html.escape(post_id)}</code> видалено з бази.</b>",
                parse_mode="HTML",
            )
        else:
            await message.answer(f"❌ Пост <code>{html.escape(post_id)}</code> не знайдено.", parse_mode="HTML")
    except Exception as e:
        logger.exception("Помилка видалення поста")
        await message.answer(f"❌ <b>Помилка:</b> <code>{html.escape(str(e))}</code>", parse_mode="HTML")
