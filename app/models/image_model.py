"""Модели данных для изображений.

Принципы:
- SRP: только структура данных, без логики обработки.
- Чистый код: неизменяемость (`frozen=True`) для предсказуемости.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass(frozen=True)
class ImageData:
    """Неизменяемая модель изображения и его метаданные.

    Fields:
        path: Путь к исходному файлу.
        pil_image: Загруженное изображение PIL.
        width: Ширина, px.
        height: Высота, px.
        mode: Режим PIL, например "RGBA".
        size_bytes: Размер файла, если доступен.
    """
    path: Path
    pil_image: Image.Image
    width: int
    height: int
    mode: str
    size_bytes: Optional[int]


