"""Service to extract metadata from YouTube videos or song links."""

import json
import re
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional


def fetch_youtube_oembed(url: str) -> Optional[Dict[str, Any]]:
    """
    Швидке та надлегке отримання метаданих через офіційний oEmbed API YouTube.
    Споживає 0 додаткової пам'яті (без імпорту важких бібліотек yt-dlp).
    """
    try:
        encoded = urllib.parse.quote(url, safe="")
        endpoint = f"https://www.youtube.com/oembed?url={encoded}&format=json"
        req = urllib.request.Request(
            endpoint,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "title": data.get("title") or "Unknown Song",
                    "artist": data.get("author_name") or "Unknown Artist",
                    "channel": data.get("author_name") or "",
                    "description": "",
                    "duration": 0,
                    "url": url,
                    "tags": [],
                    "thumbnail": data.get("thumbnail_url") or "",
                    "view_count": 0,
                }
    except Exception:
        pass
    return None


class YouTubeService:
    """Extracts song/video information from YouTube URLs with memory optimization."""

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Check if a string looks like a YouTube link."""
        if not isinstance(url, str):
            return False
        patterns = [
            r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+",
            r"(https?://)?music\.youtube\.com/.+",
        ]
        return any(re.match(p, url.strip()) for p in patterns)

    def extract_song_info(self, url_or_query: str) -> Dict[str, Any]:
        """
        Extract video/song metadata.
        1. Для прямих YouTube-посилань спочатку пробує надлегкий oEmbed (економить ~40 МБ RAM).
        2. Тільки якщо потрібно (пошук або детальний парсинг) — ліниво завантажує yt-dlp.
        """
        target = url_or_query.strip()
        is_direct_url = self.is_youtube_url(target)

        # 1. Спроба надлегкого oEmbed
        if is_direct_url:
            oembed_info = fetch_youtube_oembed(target)
            if oembed_info:
                return oembed_info

        # 2. Лінивий імпорт yt-dlp лише за потреби
        try:
            import yt_dlp
        except ImportError:
            return {
                "title": url_or_query,
                "url": url_or_query,
                "description": "",
                "artist": "",
                "duration": 0,
                "tags": [],
            }

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        search_query = target if is_direct_url else f"ytsearch1:{target}"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]

                return {
                    "title": info.get("title") or "Unknown Song",
                    "artist": info.get("artist") or info.get("creator") or info.get("uploader") or "Unknown Artist",
                    "channel": info.get("channel") or info.get("uploader") or "",
                    "description": (info.get("description") or "")[:1500],
                    "duration": info.get("duration") or 0,
                    "url": info.get("webpage_url") or url_or_query,
                    "tags": (info.get("tags") or [])[:10],
                    "thumbnail": info.get("thumbnail") or "",
                    "view_count": info.get("view_count") or 0,
                }
        except Exception as e:
            return {
                "title": url_or_query,
                "artist": "Unknown Artist",
                "channel": "",
                "description": f"Could not fetch YouTube metadata: {str(e)}",
                "duration": 0,
                "url": url_or_query,
                "tags": [],
                "error": str(e),
            }
