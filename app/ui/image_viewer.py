from __future__ import annotations

from typing import Callable, Optional, Tuple

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk


class ImageViewer(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk | tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0, bg=self._get_canvas_bg())
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._original_image: Optional[Image.Image] = None
        self._rgba_sampling_image: Optional[Image.Image] = None
        self._tk_image: Optional[ImageTk.PhotoImage] = None

        self._scale_factor: float = 1.0
        self._fit_scale_factor: float = 1.0
        self._image_top_left: Tuple[int, int] = (0, 0)

        self.on_cursor_move: Optional[Callable[[Optional[int], Optional[int], Optional[Tuple[int, int, int, int]]], None]] = None

        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._canvas.bind("<Motion>", self._on_mouse_move)
        self._canvas.bind("<Leave>", self._on_mouse_leave)

    # ---- Public API ----
    def set_image(self, image: Image.Image) -> None:
        self._original_image = image
        self._rgba_sampling_image = image if image.mode == "RGBA" else image.convert("RGBA")
        self._compute_fit_scale()
        self._scale_factor = self._fit_scale_factor
        self._render_image()

    def set_zoom_to_fit(self) -> None:
        self._compute_fit_scale()
        self._scale_factor = self._fit_scale_factor
        self._render_image()

    def set_zoom_percent(self, zoom_percent: int) -> None:
        self._scale_factor = max(0.1, min(4.0, zoom_percent / 100.0))
        self._render_image()

    def get_zoom_percent(self) -> int:
        return int(round(self._scale_factor * 100))

    # ---- Internals ----
    def _on_canvas_resize(self, _event: tk.Event) -> None:
        if self._original_image is None:
            return
        self._compute_fit_scale()
        # do not force fit scale if user zoomed manually, but rerender to center
        self._render_image()

    def _render_image(self) -> None:
        self._canvas.delete("all")
        if self._original_image is None:
            return

        img_w, img_h = self._original_image.size
        scaled_w = max(1, int(img_w * self._scale_factor))
        scaled_h = max(1, int(img_h * self._scale_factor))
        resized = self._original_image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(resized)

        canvas_w = int(self._canvas.winfo_width())
        canvas_h = int(self._canvas.winfo_height())
        x = max(0, (canvas_w - scaled_w) // 2)
        y = max(0, (canvas_h - scaled_h) // 2)
        self._image_top_left = (x, y)

        self._canvas.create_image(x, y, image=self._tk_image, anchor="nw")

    def _compute_fit_scale(self) -> None:
        if self._original_image is None:
            self._fit_scale_factor = 1.0
            return
        canvas_w = max(1, int(self._canvas.winfo_width()))
        canvas_h = max(1, int(self._canvas.winfo_height()))
        img_w, img_h = self._original_image.size
        if img_w == 0 or img_h == 0:
            self._fit_scale_factor = 1.0
            return
        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        self._fit_scale_factor = max(0.1, min(4.0, min(scale_w, scale_h)))

    def _on_mouse_move(self, event: tk.Event) -> None:
        if self._original_image is None or self.on_cursor_move is None:
            return
        img_x, img_y = self._canvas_to_image_coords(event.x, event.y)
        if img_x is None or img_y is None:
            self.on_cursor_move(None, None, None)
            return
        rgba = self._rgba_sampling_image.getpixel((img_x, img_y)) if self._rgba_sampling_image else None
        self.on_cursor_move(img_x, img_y, rgba)

    def _on_mouse_leave(self, _event: tk.Event) -> None:
        if self.on_cursor_move:
            self.on_cursor_move(None, None, None)

    def _canvas_to_image_coords(self, cx: int, cy: int) -> Tuple[Optional[int], Optional[int]]:
        if self._original_image is None:
            return None, None
        img_w, img_h = self._original_image.size
        ox, oy = self._image_top_left
        dx = cx - ox
        dy = cy - oy
        if dx < 0 or dy < 0:
            return None, None
        x = int(dx / self._scale_factor)
        y = int(dy / self._scale_factor)
        if x < 0 or y < 0 or x >= img_w or y >= img_h:
            return None, None
        return x, y

    def _get_canvas_bg(self) -> str:
        # Soft checker-like color; CTk does not expose canvas theme, so pick neutral
        return "#1f1f1f" if ctk.get_appearance_mode().lower() == "dark" else "#f2f2f2"


