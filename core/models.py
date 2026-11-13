"""Data models for posts and review system."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PostStatus(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"


class PostSource(str, Enum):
    YOUTUBE = "youtube"
    SONG_TEXT = "song_text"
    IMAGE = "image"


class PostItem(BaseModel):
    """Represents a generated song/image post item."""
    id: str = Field(..., description="Unique post identifier")
    title: str = Field(..., description="Post title or headline")
    content: str = Field(..., description="Main post text / review")
    hashtags: List[str] = Field(default_factory=list, description="Recommended hashtags")
    source_type: PostSource = Field(..., description="Source type: youtube, song_text, image")
    source_ref: str = Field("", description="URL, song name, or image file path")
    status: PostStatus = Field(default=PostStatus.DRAFT, description="Review status")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    review_notes: Optional[str] = Field(None, description="User notes or review comments")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata like artist, duration, etc.")

    def update_content(self, new_content: Optional[str] = None, new_title: Optional[str] = None, new_status: Optional[PostStatus] = None, notes: Optional[str] = None):
        """Update post content and refresh updated_at timestamp."""
        if new_content is not None:
            self.content = new_content
        if new_title is not None:
            self.title = new_title
        if new_status is not None:
            self.status = new_status
        if notes is not None:
            self.review_notes = notes
        self.updated_at = datetime.now(timezone.utc).isoformat()
