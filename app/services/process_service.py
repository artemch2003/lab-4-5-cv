from __future__ import annotations

from PIL import Image, ImageOps


class ProcessService:
    def to_grayscale(self, image: Image.Image) -> Image.Image:
        # Возвращает изображение RGBA в оттенках серого (альфа сохранена)
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        rgb = image.convert("RGB")
        gray = ImageOps.grayscale(rgb)  # L
        rgba_gray = Image.merge("RGBA", (gray, gray, gray, image.split()[3]))
        return rgba_gray


