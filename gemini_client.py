"""
Gemini API Client Module
Supports Google's modern Interactions API with Gemini 3.8 Flash and Gemini 3.5 Flash-Lite.
"""

import os
import mimetypes
from pathlib import Path
from typing import Generator, Optional, List, Dict, Any, Union
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()


class GeminiClient:
    """Wrapper client for Google Gemini API."""

    DEFAULT_SYSTEM_INSTRUCTION = (
        "Ти професійний ШІ-асистент. Відповідай на всі запити виключно українською мовою, "
        "грамотно, змістовно та зрозуміло."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gemini-3.5-flash-lite",
    ):
        """
        Initialize the Gemini client.
        
        :param api_key: Gemini API key. Defaults to GEMINI_API_KEY from environment or .env
        :param default_model: Recommended models:
            - 'gemini-3.5-flash-lite': Fast, cost-efficient, low latency (default)
            - 'gemini-3.8-flash': Balanced high-performance for multimodal and reasoning
            - 'gemini-4-argon': Most capable model for deep reasoning and research
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key not found! Please set GEMINI_API_KEY in your .env file or environment."
            )
        
        self.client = genai.Client(api_key=self.api_key)
        self.default_model = default_model

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Generate text response for a single prompt.
        """
        kwargs: Dict[str, Any] = {
            "model": model or self.default_model,
            "input": prompt,
            "system_instruction": system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION,
        }

        interaction = self.client.interactions.create(**kwargs)
        return interaction.output_text or ""

    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Stream text response chunks in real-time.
        """
        kwargs: Dict[str, Any] = {
            "model": model or self.default_model,
            "input": prompt,
            "stream": True,
            "system_instruction": system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION,
        }

        events = self.client.interactions.create(**kwargs)
        for event in events:
            if event.event_type == "step.delta":
                if hasattr(event.delta, "type") and event.delta.type == "text":
                    yield event.delta.text

    def create_conversation(self, model: Optional[str] = None) -> "GeminiChat":
        """Start a new stateful multi-turn conversation."""
        return GeminiChat(self, model=model or self.default_model)

    def analyze_audio(
        self,
        file_path: Union[str, Path],
        prompt: str = "Зроби розшифровку (транскрипцію) та детальний аналіз цього аудіофайлу українською мовою. Опиши настрій, темп, звучання та зміст.",
        model: Optional[str] = None,
    ) -> str:
        """
        Upload and analyze an audio file (mp3, wav, flac, ogg, etc.).
        
        :param file_path: Path to the local audio file
        :param prompt: Instructions for the model regarding the audio
        :param model: Gemini model (gemini-3.8-flash or gemini-3.5-flash-lite)
        :return: Analysis or transcription text
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "audio/wav" if path.suffix.lower() == ".wav" else "audio/mp3"

        # Upload file to Gemini Files API
        uploaded_file = self.client.files.upload(file=str(path))

        interaction = self.client.interactions.create(
            model=model or self.default_model,
            input=[
                {"type": "text", "text": prompt},
                {"type": "audio", "uri": uploaded_file.uri, "mime_type": mime_type},
            ],
        )
        return interaction.output_text or ""


class GeminiChat:
    """Stateful multi-turn conversation session."""

    def __init__(self, client: GeminiClient, model: str):
        self.gemini_client = client
        self.model = model
        self.last_interaction_id: Optional[str] = None

    def send_message(self, message: str) -> str:
        """Send message maintaining context across turns."""
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "input": message,
            "system_instruction": self.gemini_client.DEFAULT_SYSTEM_INSTRUCTION,
        }
        if self.last_interaction_id:
            kwargs["previous_interaction_id"] = self.last_interaction_id

        interaction = self.gemini_client.client.interactions.create(**kwargs)
        self.last_interaction_id = interaction.id
        return interaction.output_text or ""
