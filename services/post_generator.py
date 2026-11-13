"""Orchestrator service connecting YouTube extraction, Gemini AI, and Post Storage."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from core.models import PostItem, PostStatus, PostSource
from core.storage import PostStorage
from services.youtube_service import YouTubeService
from services.gemini_service import GeminiService


class PostGeneratorService:
    """Core service for generating, reviewing, editing, and saving posts."""

    def __init__(
        self,
        storage: Optional[PostStorage] = None,
        gemini_service: Optional[GeminiService] = None,
        youtube_service: Optional[YouTubeService] = None,
    ):
        self.storage = storage or PostStorage()
        self.gemini = gemini_service or GeminiService()
        self.youtube = youtube_service or YouTubeService()

    def _generate_post_id(self, prefix: str = "post") -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:6]
        return f"{prefix}_{timestamp}_{short_id}"

    def create_post_from_song(
        self,
        song_query_or_url: str,
        custom_instructions: Optional[str] = None,
    ) -> PostItem:
        """
        Extract song details (from YouTube or text title) and generate a post using Gemini.
        Saves the post as a draft in storage.
        """
        is_yt = self.youtube.is_youtube_url(song_query_or_url)
        source_type = PostSource.YOUTUBE if is_yt else PostSource.SONG_TEXT

        # Extract YouTube info if URL or search term
        song_info = self.youtube.extract_song_info(song_query_or_url)

        # Generate text via Gemini
        generated = self.gemini.generate_song_post(
            song_info=song_info,
            custom_instructions=custom_instructions,
        )

        post = PostItem(
            id=self._generate_post_id("song"),
            title=generated.get("title", f"Музичний огляд: {song_info.get('title')}"),
            content=generated.get("content", ""),
            hashtags=generated.get("hashtags", []),
            source_type=source_type,
            source_ref=song_info.get("url") or song_query_or_url,
            status=PostStatus.DRAFT,
            metadata={
                "artist": song_info.get("artist"),
                "duration": song_info.get("duration"),
                "thumbnail": song_info.get("thumbnail"),
                "view_count": song_info.get("view_count"),
            },
        )

        # Persist to .json storage
        self.storage.save(post)
        return post

    def create_post_from_image(
        self,
        image_path: str,
        custom_instructions: Optional[str] = None,
    ) -> PostItem:
        """
        Analyze an image and generate a creative post using Gemini.
        Saves the post as a draft in storage.
        """
        generated = self.gemini.analyze_image_and_generate_post(
            image_path=image_path,
            user_prompt=custom_instructions,
        )

        post = PostItem(
            id=self._generate_post_id("img"),
            title=generated.get("title", f"Пост за зображенням: {image_path}"),
            content=generated.get("content", ""),
            hashtags=generated.get("hashtags", []),
            source_type=PostSource.IMAGE,
            source_ref=image_path,
            status=PostStatus.DRAFT,
            metadata={"image_path": str(image_path)},
        )

        # Persist to .json storage
        self.storage.save(post)
        return post

    def get_all_posts(self) -> List[PostItem]:
        """Return all stored posts."""
        return self.storage.get_all()

    def get_post(self, post_id: str) -> Optional[PostItem]:
        """Get a post by ID."""
        return self.storage.get_by_id(post_id)

    def edit_post(
        self,
        post_id: str,
        new_content: Optional[str] = None,
        new_title: Optional[str] = None,
        new_status: Optional[PostStatus] = None,
        review_notes: Optional[str] = None,
    ) -> Optional[PostItem]:
        """Edit post text, title, or review status."""
        return self.storage.update(
            post_id=post_id,
            new_content=new_content,
            new_title=new_title,
            new_status=new_status,
            review_notes=review_notes,
        )

    def approve_post(self, post_id: str, notes: Optional[str] = None) -> Optional[PostItem]:
        """Mark post as approved."""
        return self.storage.update(
            post_id=post_id,
            new_status=PostStatus.APPROVED,
            review_notes=notes,
        )

    def delete_post(self, post_id: str) -> bool:
        """Delete a post from storage."""
        return self.storage.delete(post_id)
