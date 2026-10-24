from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, APIC
from mutagen.mp3 import MP3


def is_mp3(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".mp3"


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in {
        ".jpg",
        ".jpeg",
        ".png",
    }


def get_mime_type(filename: str) -> str:
    if Path(filename).suffix.lower() == ".png":
        return "image/png"

    return "image/jpeg"


def check_mp3(path: Path) -> bool:
    try:
        audio = MP3(path)
        return audio.info is not None
    except Exception:
        return False


def replace_cover(
    mp3_path: Path,
    image_path: Path,
):
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    # Видаляємо попередню обкладинку.
    tags.delall("APIC")

    # Додаємо нову обкладинку.
    tags.add(
        APIC(
            encoding=3,
            mime=get_mime_type(image_path.name),
            type=3,
            desc="Cover",
            data=image_path.read_bytes(),
        )
    )

    tags.save(mp3_path, v2_version=3)