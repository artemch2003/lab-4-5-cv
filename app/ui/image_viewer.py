"""Виджет просмотра изображений: масштабирование, панорамирование и режимы сравнения.

Принципы:
- SRP: отвечает только за представление и интеракции с изображением.
- Чистый код: чёткое разделение публичного API и внутренних обработчиков событий.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk


class ImageViewer(ctk.CTkFrame):
    """Канва с логикой отображения «до/после», шторки и side-by-side."""
    def __init__(self, master: ctk.CTk | tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0, bg=self._get_canvas_bg())
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._original_image: Optional[Image.Image] = None
        self._processed_image: Optional[Image.Image] = None
        self._rgba_sampling_image: Optional[Image.Image] = None  # always RGBA original for sampling
        self._tk_image_before: Optional[ImageTk.PhotoImage] = None
        self._tk_image_after: Optional[ImageTk.PhotoImage] = None

        self._scale_factor: float = 1.0
        self._fit_scale_factor: float = 1.0
        self._image_top_left: Optional[Tuple[int, int]] = None

        # panning state
        self._is_panning: bool = False
        self._pan_start_canvas_xy: Optional[Tuple[int, int]] = None
        self._pan_start_top_left: Optional[Tuple[int, int]] = None

        self.on_cursor_move: Optional[Callable[[Optional[int], Optional[int], Optional[Tuple[int, int, int, int]]], None]] = None
        self.on_zoom_change: Optional[Callable[[int], None]] = None

        # compare modes: "off" | "wipe" | "side_by_side"
        self._compare_mode: str = "off"
        self._wipe_ratio: float = 0.5
        self._hold_before_active: bool = False

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

        # Hold space to preview "before"
        self._canvas.bind("<KeyPress-space>", self._on_space_down)
        self._canvas.bind("<KeyRelease-space>", self._on_space_up)

    # ---- Public API ----
    def set_image(self, image: Image.Image) -> None:
        """Устанавливает исходное изображение и сбрасывает состояние зума/панорамирования."""
        self._original_image = image
        self._processed_image = None
        self._rgba_sampling_image = image if image.mode == "RGBA" else image.convert("RGBA")
        self._compute_fit_scale()
        self._scale_factor = self._fit_scale_factor
        self._image_top_left = None  # reset to center
        self._render_image()

    def set_processed_image(self, image: Optional[Image.Image]) -> None:
        """Устанавливает обработанное изображение (может быть None) и перерисовывает виджет."""
        self._processed_image = image
        self._render_image()

    def set_zoom_to_fit(self) -> None:
        """Масштабирует изображение так, чтобы оно целиком помещалось в доступную область."""
        self._compute_fit_scale()
        self._scale_factor = self._fit_scale_factor
        self._image_top_left = None  # reset to center
        self._render_image()

    def set_zoom_percent(self, zoom_percent: int) -> None:
        """Устанавливает масштаб в процентах (10–400%)."""
        self._scale_factor = max(0.1, min(4.0, zoom_percent / 100.0))
        self._render_image()

    def get_zoom_percent(self) -> int:
        """Возвращает текущий масштаб в процентах."""
        return int(round(self._scale_factor * 100))

    def set_compare_mode(self, mode: str) -> None:
        """Устанавливает режим сравнения: 'Нет' | 'Шторка' | '2-up'."""
        # mode: "Нет" | "Шторка" | "2-up" -> internal: off | wipe | side_by_side
        mapping = {"Нет": "off", "Шторка": "wipe", "2-up": "side_by_side"}
        self._compare_mode = mapping.get(mode, "off")
        self._image_top_left = None  # recenter
        self._render_image()

    def set_wipe_percent(self, percent: int) -> None:
        """Устанавливает положение «шторки» (0–100%) и перерисовывает при активном режиме."""
        self._wipe_ratio = max(0.0, min(1.0, percent / 100.0))
        if self._compare_mode == "wipe":
            self._render_image()

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

        canvas_w = int(self._canvas.winfo_width())
        canvas_h = int(self._canvas.winfo_height())

        img_w, img_h = self._original_image.size
        scaled_w = max(1, int(img_w * self._scale_factor))
        scaled_h = max(1, int(img_h * self._scale_factor))

        # prepare resized images as needed
        show_after = (self._processed_image is not None) and not self._hold_before_active
        resized_before = self._original_image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        resized_after = None
        if self._processed_image is not None:
            resized_after = self._processed_image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

        # content dimensions (for panning bounds) differ by mode
        if self._compare_mode == "side_by_side" and resized_after is not None:
            content_w = scaled_w * 2 + 16
            content_h = scaled_h
        else:
            content_w = scaled_w
            content_h = scaled_h

        # compute allowed top-left range
        if content_w <= canvas_w:
            min_x = max_x = (canvas_w - content_w) // 2
        else:
            min_x = canvas_w - content_w
            max_x = 0
        if content_h <= canvas_h:
            min_y = max_y = (canvas_h - content_h) // 2
        else:
            min_y = canvas_h - content_h
            max_y = 0

        if self._image_top_left is None:
            x = (canvas_w - content_w) // 2 if content_w <= canvas_w else 0
            y = (canvas_h - content_h) // 2 if content_h <= canvas_h else 0
            self._image_top_left = (x, y)
        else:
            ox, oy = self._image_top_left
            x = max(min_x, min(max_x, ox))
            y = max(min_y, min(max_y, oy))
            self._image_top_left = (x, y)

        ox, oy = self._image_top_left

        # draw by mode
        if self._compare_mode == "wipe" and resized_after is not None:
            split = int(round(scaled_w * self._wipe_ratio))
            left_crop = resized_before.crop((0, 0, split, scaled_h))
            right_crop = (resized_after if show_after else resized_before).crop((split, 0, scaled_w, scaled_h))

            self._tk_image_before = ImageTk.PhotoImage(left_crop)
            self._canvas.create_image(ox, oy, image=self._tk_image_before, anchor="nw")

            self._tk_image_after = ImageTk.PhotoImage(right_crop)
            self._canvas.create_image(ox + split, oy, image=self._tk_image_after, anchor="nw")
        elif self._compare_mode == "side_by_side" and resized_after is not None:
            gap = 16
            left_img = resized_before
            right_img = resized_after if show_after else resized_before

            self._tk_image_before = ImageTk.PhotoImage(left_img)
            self._canvas.create_image(ox, oy, image=self._tk_image_before, anchor="nw")

            self._tk_image_after = ImageTk.PhotoImage(right_img)
            self._canvas.create_image(ox + scaled_w + gap, oy, image=self._tk_image_after, anchor="nw")
        else:
            # single image
            draw_img = resized_after if (show_after and resized_after is not None) else resized_before
            self._tk_image_before = ImageTk.PhotoImage(draw_img)
            self._canvas.create_image(ox, oy, image=self._tk_image_before, anchor="nw")

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
        img_x, img_y, sample_from_after = self._canvas_to_image_coords(event.x, event.y)
        if img_x is None or img_y is None:
            self.on_cursor_move(None, None, None)
            return
        if sample_from_after and self._processed_image is not None and not self._hold_before_active:
            rgba_img = self._processed_image if self._processed_image.mode == "RGBA" else self._processed_image.convert("RGBA")
            rgba = rgba_img.getpixel((img_x, img_y))
        else:
            rgba = self._rgba_sampling_image.getpixel((img_x, img_y)) if self._rgba_sampling_image else None
        self.on_cursor_move(img_x, img_y, rgba)

    def _on_mouse_leave(self, _event: tk.Event) -> None:
        if self.on_cursor_move:
            self.on_cursor_move(None, None, None)

    def _canvas_to_image_coords(self, cx: int, cy: int) -> Tuple[Optional[int], Optional[int], bool]:
        if self._original_image is None:
            return None, None, False
        img_w, img_h = self._original_image.size
        if self._image_top_left is None:
            return None, None, False
        ox, oy = self._image_top_left
        dx = cx - ox
        dy = cy - oy
        if dx < 0 or dy < 0:
            return None, None, False

        scaled_w = max(1, int(img_w * self._scale_factor))
        scaled_h = max(1, int(img_h * self._scale_factor))

        # Determine which image under cursor in compare modes
        if self._compare_mode == "side_by_side" and self._processed_image is not None:
            gap = 16
            if 0 <= dx < scaled_w and 0 <= dy < scaled_h:
                x = int(dx / self._scale_factor)
                y = int(dy / self._scale_factor)
                if 0 <= x < img_w and 0 <= y < img_h:
                    return x, y, False  # before
            right_dx = dx - (scaled_w + gap)
            if 0 <= right_dx < scaled_w and 0 <= dy < scaled_h:
                x = int(right_dx / self._scale_factor)
                y = int(dy / self._scale_factor)
                if 0 <= x < img_w and 0 <= y < img_h:
                    return x, y, True  # after
            return None, None, False

        # Single or wipe
        if 0 <= dx < scaled_w and 0 <= dy < scaled_h:
            x = int(dx / self._scale_factor)
            y = int(dy / self._scale_factor)
            if 0 <= x < img_w and 0 <= y < img_h:
                if self._compare_mode == "wipe" and self._processed_image is not None:
                    split = int(round(scaled_w * self._wipe_ratio))
                    sample_after = dx >= split and not self._hold_before_active
                    return x, y, sample_after
                return x, y, False
        return None, None, False

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
        self._canvas.focus_set()
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

    def _on_space_down(self, _event: tk.Event) -> None:
        if self._compare_mode in ("off", "wipe"):
            if not self._hold_before_active:
                self._hold_before_active = True
                self._render_image()

    def _on_space_up(self, _event: tk.Event) -> None:
        if self._compare_mode in ("off", "wipe"):
            if self._hold_before_active:
                self._hold_before_active = False
                self._render_image()


