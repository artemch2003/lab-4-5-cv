from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

from app.models.image_model import ImageData


class ImageService:
    def load_image(self, file_path: str | Path) -> ImageData:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Файл не найден: {path}")

        try:
            pil_image = Image.open(path).convert("RGBA")
        except UnidentifiedImageError as exc:
            raise ValueError(f"Файл не является изображением: {path}") from exc

        width, height = pil_image.size
        try:
            size_bytes: Optional[int] = path.stat().st_size
        except OSError:
            size_bytes = None

        return ImageData(
            path=path,
            pil_image=pil_image,
            width=width,
            height=height,
            mode=pil_image.mode,
            size_bytes=size_bytes,
        )


