from pathlib import Path
from PIL import Image
from mutagen.id3 import ID3, ID3NoHeaderError, APIC
from mutagen.mp3 import MP3


def is_mp3(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".mp3"


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }


def check_mp3(path: Path) -> bool:
    try:
        audio = MP3(path)
        return audio.info is not None
    except Exception:
        return False


def extract_metadata(mp3_path: Path) -> tuple[str | None, str | None]:
    """Дістає назву та виконавця з ID3-тегів, якщо файл надіслали як документ."""
    try:
        tags = ID3(mp3_path)
        title = str(tags["TIT2"].text[0]) if "TIT2" in tags and tags["TIT2"].text else None
        performer = str(tags["TPE1"].text[0]) if "TPE1" in tags and tags["TPE1"].text else None
        return title, performer
    except Exception:
        return None, None


def prepare_cover_images(source_path: Path, temp_dir: Path) -> tuple[Path, Path]:
    """
    Конвертує зображення у JPEG та створює два файли:
    1. embedded_path — для вшивання в ID3-тег MP3 (до 1000x1000 px).
    2. thumb_path — мініатюра для Telegram Bot API (до 320x320 px, < 200 КБ).
    """
    embedded_path = temp_dir / "embedded_cover.jpg"
    thumb_path = temp_dir / "tg_thumb.jpg"

    with Image.open(source_path) as img:
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # 1. Версія для вшивання в сам MP3-файл
        embedded_img = img.copy()
        embedded_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
        embedded_img.save(embedded_path, format="JPEG", quality=90, optimize=True)

        # 2. Мініатюра для відображення в плеєрі Telegram
        thumb_img = img.copy()
        thumb_img.thumbnail((320, 320), Image.Resampling.LANCZOS)
        thumb_img.save(thumb_path, format="JPEG", quality=85, optimize=True)

    return embedded_path, thumb_path


def replace_cover(
    mp3_path: Path,
    jpeg_cover_path: Path,
):
    """
    Замінює виключно обкладинку MP3 (ID3v2.3, JPEG),
    не зачіпаючи інші текстові метадані.
    """
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("APIC")

    tags.add(
        APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=jpeg_cover_path.read_bytes(),
        )
    )

    tags.save(
        mp3_path,
        v2_version=3,
    )