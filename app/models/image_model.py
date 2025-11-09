from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass(frozen=True)
class ImageData:
    path: Path
    pil_image: Image.Image
    width: int
    height: int
    mode: str
    size_bytes: Optional[int]


