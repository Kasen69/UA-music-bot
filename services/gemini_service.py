"""Gemini API Service for generating music posts and analyzing images."""

import base64
import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.config import GEMINI_API_KEY, DEFAULT_MODEL

logger = logging.getLogger(__name__)


class GeminiService:
    """Interactions & models-based Gemini service for text and multimodal generation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")

        self._client = None
        self.model = model or DEFAULT_MODEL

    @property
    def client(self):
        """Лінива ініціалізація клієнта Gemini для збереження пам'яті."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _call_gemini_text(self, system_instruction: str, user_prompt: str) -> str:
        """
        Універсальний виклик Gemini API для тексту.
        Підтримує як Interactions API, так і класичний models.generate_content.
        """
        models_to_try = [self.model]
        for fallback in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error = None
        for current_model in models_to_try:
            # 1. Спроба через interactions.create (новий інтерфейс Google GenAI)
            try:
                if hasattr(self.client, "interactions") and hasattr(self.client.interactions, "create"):
                    interaction = self.client.interactions.create(
                        model=current_model,
                        system_instruction=system_instruction,
                        input=user_prompt,
                    )
                    out = getattr(interaction, "output_text", None) or getattr(interaction, "text", None)
                    if out:
                        return str(out)
            except Exception as e:
                logger.debug("interactions.create failed for %s: %s", current_model, e)
                last_error = e

            # 2. Спроба через models.generate_content (універсальний метод Google GenAI)
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=user_prompt,
                    config=config,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.debug("models.generate_content with config failed for %s: %s", current_model, e)
                last_error = e

            # 3. Спроба без types.GenerateContentConfig
            try:
                full_prompt = f"System: {system_instruction}\n\nUser: {user_prompt}"
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=full_prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.debug("models.generate_content basic failed for %s: %s", current_model, e)
                last_error = e

        raise RuntimeError(f"Не вдалося згенерувати відповідь через Gemini API: {last_error}")

    def _call_gemini_image(self, system_instruction: str, prompt_text: str, image_path: Path, mime_type: str) -> str:
        """
        Універсальний виклик Gemini API для мультимодальних зображень.
        """
        models_to_try = [self.model]
        for fallback in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error = None
        for current_model in models_to_try:
            # 1. Спроба через models.generate_content з PIL Image (швидко та надійно)
            try:
                from PIL import Image
                from google.genai import types

                with Image.open(image_path) as img:
                    img_copy = img.copy()

                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=[img_copy, prompt_text],
                    config=config,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.debug("models.generate_content with PIL image failed for %s: %s", current_model, e)
                last_error = e

            # 2. Спроба через Files API + interactions.create
            try:
                if hasattr(self.client, "interactions") and hasattr(self.client.interactions, "create"):
                    uploaded_file = self.client.files.upload(file=str(image_path))
                    interaction = self.client.interactions.create(
                        model=current_model,
                        system_instruction=system_instruction,
                        input=[
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image",
                                "uri": uploaded_file.uri,
                                "mime_type": uploaded_file.mime_type or mime_type,
                            },
                        ],
                    )
                    out = getattr(interaction, "output_text", None) or getattr(interaction, "text", None)
                    if out:
                        return str(out)
            except Exception as e:
                logger.debug("interactions.create with uploaded file failed for %s: %s", current_model, e)
                last_error = e

        raise RuntimeError(f"Не вдалося проаналізувати зображення через Gemini API: {last_error}")

    def _parse_structured_post(self, raw_text: str, default_title: str) -> Dict[str, Any]:
        """Extract title, content, and hashtags from raw or JSON response."""
        cleaned = raw_text.strip()
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return {
                    "title": data.get("title") or default_title,
                    "content": data.get("content") or cleaned,
                    "hashtags": data.get("hashtags") or [],
                }
            except Exception:
                pass

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return {
                    "title": data.get("title") or default_title,
                    "content": data.get("content") or cleaned,
                    "hashtags": data.get("hashtags") or [],
                }
        except Exception:
            pass

        hashtags = re.findall(r"#\w+", raw_text)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        title = default_title
        if lines:
            first_line = lines[0].replace("#", "").replace("**", "").strip()
            if len(first_line) < 100:
                title = first_line

        return {
            "title": title,
            "content": raw_text.strip(),
            "hashtags": hashtags,
        }

    def generate_song_post(
        self,
        song_info: Dict[str, Any],
        custom_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate an engaging music review / social post about a song.
        """
        title = song_info.get("title", "Unknown Title")
        artist = song_info.get("artist", "")
        desc = song_info.get("description", "")
        url = song_info.get("url", "")

        system_instruction = (
            "Ти професійний музичний куратор, рецензент та головний редактор сучасного українського музичного Telegram-каналу. "
            "Твоє завдання — за введеними даними (назва пісні та виконавця, посилання на YouTube або опис зображення) "
            "створити ідеальний, грамотний і стильний пост. "
            "ОБОВ'ЯЗКОВІ ПЕРЕВІРКИ ТА УМОВИ (виконуй перед генерацією): "
            "1. Автори музики: Аналізуй виключно справжніх творців/виконавців музики. Повністю ігноруй назви каналів, ютуберів чи подкастерів. "
            "2. Перевірка на українське походження: Музика має належати українським виконавцям/авторам. Якщо виконавець не український, "
            "поверни у полі 'content' єдине речення: 'Цей контент не належить українській музичній сцені.' "
            "3. Перевірка посилання: Якщо передано посилання, перевір, чи веде воно на музичний трек або альбом. Якщо ні, "
            "поверни у полі 'content' єдине речення: 'Це посилання не веде на музичний трек.' "
            "4. Формат: Визнач, чи це альбом/дискографія, чи окремий трек, і відповідно адаптуй текст. "
            "СТРУКТУРА ПОСТУ (для поля 'content'): "
            "1. Цитата-крюк: Починай із влучної цитати з пісні або атмосферного рядка, взятого в лапки «...». "
            "2. Емоційний вступ: З нового абзацу — емоційне занурення з емодзі на початку (наприклад, 🖤 Ця пісня [Виконавець] — ...). "
            "3. Основний текст: 2-3 короткі абзаци про музику, звучання, текст та вайб без штучного пафосу. "
            "4. Заклик до коментарів (CTA): Окремий абзац, що починається з емодзі 👇 і містить живе запитання до підписників. "
            "Відповідь повертай ТІЛЬКИ у форматі валідного JSON об'єкта з трьома полями: "
            "'title' (привабливий український заголовок для поста), "
            "'content' (основний текст поста українською мовою, гарно відформатований на абзаци з одинарними відступами та емодзі), "
            "'hashtags' (масив із 4-8 релевантних хештегів українською та англійською мовами)."
        )

        user_prompt = f"""
Інформація про пісню:
- Назва: {title}
- Виконавець/Канал: {artist}
- Посилання: {url}
- Опис/Уривок: {desc[:800]}

Додаткові побажання користувача: {custom_instructions or "Створи захоплюючий пост-огляд українською мовою, розкриваючи вайб і глибину треку."}

Згенеруй JSON пост українською мовою зараз.
"""
        raw_output = self._call_gemini_text(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
        )
        return self._parse_structured_post(raw_output, default_title=f"Огляд: {title}")

    def analyze_image_and_generate_post(
        self,
        image_path: str,
        user_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Аналізує зображення (обкладинка альбому, постер, фото з концерту) та створює пост українською мовою.
        """
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"Файл зображення не знайдено за шляхом: {image_path}")

        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"

        system_instruction = (
            "Ти креативний візуальний куратор, музичний історик та контент-мейкер. "
            "Твоє завдання — детально проаналізувати надане зображення (естетику, колірну гаму, настрій, "
            "видимий текст, символи, стиль обкладинки/постера) і написати захоплюючий, стильний пост ВИКЛЮЧНО УКРАЇНСЬКОЮ МОВОЮ. "
            "Відповідь повертай ТІЛЬКИ у форматі валідного JSON об'єкта з трьома обов'язковими полями: "
            "'title' (яскравий український заголовок, що передає настрій зображення), "
            "'content' (текст поста українською мовою: опис візуального вайбу, асоціацій з музикою, емоцій та атмосфери), "
            "'hashtags' (масив із 4-8 відповідних хештегів українською та англійською мовами)."
        )

        prompt_text = user_prompt or (
            "Уважно проаналізуй це зображення і напиши надихаючий та атмосферний пост українською мовою "
            "про його стиль, настрій та музичні асоціації."
        )

        raw_output = self._call_gemini_image(
            system_instruction=system_instruction,
            prompt_text=prompt_text,
            image_path=path,
            mime_type=mime_type,
        )
        return self._parse_structured_post(
            raw_output,
            default_title=f"Аналіз зображення: {path.name}",
        )
