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
        self._image_top_left: Optional[Tuple[int, int]] = None

        # panning state
        self._is_panning: bool = False
        self._pan_start_canvas_xy: Optional[Tuple[int, int]] = None
        self._pan_start_top_left: Optional[Tuple[int, int]] = None

        self.on_cursor_move: Optional[Callable[[Optional[int], Optional[int], Optional[Tuple[int, int, int, int]]], None]] = None
        self.on_zoom_change: Optional[Callable[[int], None]] = None

        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._canvas.bind("<Motion>", self._on_mouse_move)
        self._canvas.bind("<Leave>", self._on_mouse_leave)

        # Mouse wheel zoom (cross-platform)
        self._canvas.bind("<MouseWheel>", self._on_mouse_wheel)      # Windows/macOS
        self._canvas.bind("<Button-4>", self._on_mouse_wheel_linux)  # Linux scroll up
        self._canvas.bind("<Button-5>", self._on_mouse_wheel_linux)  # Linux scroll down

        # Panning with left mouse drag
        self._canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self._canvas.bind("<B1-Motion>", self._on_pan_move)
        self._canvas.bind("<ButtonRelease-1>", self._on_pan_end)

    # ---- Public API ----
    def set_image(self, image: Image.Image) -> None:
        self._original_image = image
        self._rgba_sampling_image = image if image.mode == "RGBA" else image.convert("RGBA")
        self._compute_fit_scale()
        self._scale_factor = self._fit_scale_factor
        self._image_top_left = None  # reset to center
        self._render_image()

    def set_zoom_to_fit(self) -> None:
        self._compute_fit_scale()
        self._scale_factor = self._fit_scale_factor
        self._image_top_left = None  # reset to center
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

        # compute allowed range for top-left; center if smaller
        if scaled_w <= canvas_w:
            min_x = max_x = (canvas_w - scaled_w) // 2
        else:
            min_x = canvas_w - scaled_w
            max_x = 0
        if scaled_h <= canvas_h:
            min_y = max_y = (canvas_h - scaled_h) // 2
        else:
            min_y = canvas_h - scaled_h
            max_y = 0

        if self._image_top_left is None:
            x = (canvas_w - scaled_w) // 2 if scaled_w <= canvas_w else 0
            y = (canvas_h - scaled_h) // 2 if scaled_h <= canvas_h else 0
            self._image_top_left = (x, y)
        else:
            ox, oy = self._image_top_left
            x = max(min_x, min(max_x, ox))
            y = max(min_y, min(max_y, oy))
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
        if self._image_top_left is None:
            return None, None
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

    # ---- Mouse wheel zoom ----
    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if self._original_image is None:
            return
        delta = event.delta
        if delta == 0:
            return
        factor = 1.1 if delta > 0 else 1.0 / 1.1
        self._zoom_at_point(event.x, event.y, factor)

    def _on_mouse_wheel_linux(self, event: tk.Event) -> None:
        # On X11, Button-4 is up, Button-5 is down
        if self._original_image is None:
            return
        if getattr(event, "num", None) == 4:
            factor = 1.1
        else:
            factor = 1.0 / 1.1
        self._zoom_at_point(event.x, event.y, factor)

    def _zoom_at_point(self, cx: int, cy: int, factor: float) -> None:
        # anchor zoom under cursor; compute image coord before zoom
        if self._image_top_left is None or self._original_image is None:
            return
        old_scale = self._scale_factor
        new_scale = max(0.1, min(4.0, old_scale * factor))
        if abs(new_scale - old_scale) < 1e-6:
            return

        ox, oy = self._image_top_left
        ix = (cx - ox) / old_scale
        iy = (cy - oy) / old_scale

        # set new scale
        self._scale_factor = new_scale

        # compute new top-left so that (ix,iy) stays under (cx,cy)
        nx = int(round(cx - ix * new_scale))
        ny = int(round(cy - iy * new_scale))
        self._image_top_left = (nx, ny)
        self._render_image()

        if self.on_zoom_change:
            self.on_zoom_change(self.get_zoom_percent())

    # ---- Panning ----
    def _on_pan_start(self, event: tk.Event) -> None:
        if self._image_top_left is None:
            return
        self._is_panning = True
        self._pan_start_canvas_xy = (event.x, event.y)
        self._pan_start_top_left = self._image_top_left

    def _on_pan_move(self, event: tk.Event) -> None:
        if not self._is_panning or self._pan_start_canvas_xy is None or self._pan_start_top_left is None:
            return
        sx, sy = self._pan_start_canvas_xy
        ox, oy = self._pan_start_top_left
        dx = event.x - sx
        dy = event.y - sy
        self._image_top_left = (ox + dx, oy + dy)
        self._render_image()

    def _on_pan_end(self, _event: tk.Event) -> None:
        self._is_panning = False
        self._pan_start_canvas_xy = None
        self._pan_start_top_left = None


