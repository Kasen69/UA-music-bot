"""JSON-based persistent storage for posts with review and edit support."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from core.config import STORAGE_FILE
from core.models import PostItem, PostStatus


class PostStorage:
    """Manages reading and writing posts to a .json file."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = Path(file_path or STORAGE_FILE)
        self._ensure_storage_file()

    def _ensure_storage_file(self):
        """Ensure the storage JSON file exists."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_raw([])

    def _read_raw(self) -> List[Dict[str, Any]]:
        """Read raw json records from disk."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_raw(self, data: List[Dict[str, Any]]):
        """Write raw json records to disk formatted with indent."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> List[PostItem]:
        """Retrieve all posts."""
        raw_items = self._read_raw()
        posts = []
        for item in raw_items:
            try:
                posts.append(PostItem.model_validate(item))
            except Exception:
                continue
        return posts

    def get_by_id(self, post_id: str) -> Optional[PostItem]:
        """Find a post by its ID."""
        for post in self.get_all():
            if post.id == post_id:
                return post
        return None

    def save(self, post: PostItem) -> PostItem:
        """Save a new post or update an existing one in the JSON file."""
        posts = self.get_all()
        existing_index = next((i for i, p in enumerate(posts) if p.id == post.id), None)
        
        if existing_index is not None:
            posts[existing_index] = post
        else:
            posts.insert(0, post)  # Newest first

        self._write_raw([p.model_dump() for p in posts])
        return post

    def update(
        self,
        post_id: str,
        new_content: Optional[str] = None,
        new_title: Optional[str] = None,
        new_status: Optional[PostStatus] = None,
        review_notes: Optional[str] = None,
    ) -> Optional[PostItem]:
        """Update an existing post in the JSON file."""
        post = self.get_by_id(post_id)
        if not post:
            return None

        post.update_content(
            new_content=new_content,
            new_title=new_title,
            new_status=new_status,
            notes=review_notes,
        )
        return self.save(post)

    def delete(self, post_id: str) -> bool:
        """Delete a post by ID."""
        posts = self.get_all()
        filtered = [p for p in posts if p.id != post_id]
        if len(filtered) == len(posts):
            return False
        self._write_raw([p.model_dump() for p in filtered])
        return True

    def filter_by_status(self, status: PostStatus) -> List[PostItem]:
        """Get posts filtered by review status."""
        return [p for p in self.get_all() if p.status == status]
