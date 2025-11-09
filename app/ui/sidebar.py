from __future__ import annotations

from typing import Callable, Optional, Tuple

import customtkinter as ctk

from app.models.image_model import ImageData


def _rgba_to_hex(rgba: Tuple[int, int, int, int]) -> str:
    r, g, b, _a = rgba
    return f"#{r:02X}{g:02X}{b:02X}"


class Sidebar(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, width=280, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        # Callbacks
        self.on_open_file: Optional[Callable[[], None]] = None
        self.on_zoom_change: Optional[Callable[[int], None]] = None  # deprecated: controls перемещены вниз
        self.on_compare_mode_change: Optional[Callable[[str], None]] = None  # deprecated
        self.on_wipe_change: Optional[Callable[[int], None]] = None  # deprecated
        self.on_processing_change: Optional[Callable[[str], None]] = None

        # Controls
        self._title = ctk.CTkLabel(self, text="Инструменты", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.grid(row=0, column=0, padx=8, pady=(8, 4), sticky="w")

        self._open_btn = ctk.CTkButton(self, text="Открыть изображение…", command=self._emit_open_file)
        self._open_btn.grid(row=1, column=0, padx=8, pady=(0, 12), sticky="ew")

        # Нижняя панель теперь содержит управление масштабом. Эти элементы скрыты.
        self._zoom_label = ctk.CTkLabel(self, text="Масштаб (перемещено вниз)")
        self._zoom_label.grid_remove()
        self._zoom_value = ctk.StringVar(value="100%")
        self._zoom_slider = ctk.CTkSlider(self, from_=10, to=400, number_of_steps=390, command=self._on_slider_change)
        self._zoom_slider.set(100)
        self._zoom_slider.grid_remove()
        self._zoom_value_label = ctk.CTkLabel(self, textvariable=self._zoom_value)
        self._zoom_value_label.grid_remove()

        # Info section
        self._info_title = ctk.CTkLabel(self, text="Информация", font=ctk.CTkFont(size=16, weight="bold"))
        self._info_title.grid(row=2, column=0, padx=8, pady=(8, 4), sticky="w")

        self._path_val = ctk.StringVar(value="—")
        self._size_val = ctk.StringVar(value="—")
        self._dims_val = ctk.StringVar(value="—")
        self._mode_val = ctk.StringVar(value="—")

        self._info_path = ctk.CTkLabel(self, textvariable=self._path_val, wraplength=250, anchor="w", justify="left")
        self._info_size = ctk.CTkLabel(self, textvariable=self._size_val, anchor="w", justify="left")
        self._info_dims = ctk.CTkLabel(self, textvariable=self._dims_val, anchor="w", justify="left")
        self._info_mode = ctk.CTkLabel(self, textvariable=self._mode_val, anchor="w", justify="left")

        self._info_path.grid(row=3, column=0, padx=8, pady=(0, 2), sticky="ew")
        self._info_size.grid(row=4, column=0, padx=8, pady=(0, 2), sticky="ew")
        self._info_dims.grid(row=5, column=0, padx=8, pady=(0, 2), sticky="ew")
        self._info_mode.grid(row=6, column=0, padx=8, pady=(0, 10), sticky="ew")

        # Cursor section
        self._cursor_title = ctk.CTkLabel(self, text="Курсор", font=ctk.CTkFont(size=16, weight="bold"))
        self._cursor_title.grid(row=7, column=0, padx=8, pady=(8, 4), sticky="w")

        self._cursor_xy_val = ctk.StringVar(value="—")
        self._cursor_rgba_val = ctk.StringVar(value="—")
        self._cursor_hex_val = ctk.StringVar(value="—")

        self._cursor_xy = ctk.CTkLabel(self, textvariable=self._cursor_xy_val, anchor="w", justify="left")
        self._cursor_rgba = ctk.CTkLabel(self, textvariable=self._cursor_rgba_val, anchor="w", justify="left")
        self._cursor_hex = ctk.CTkLabel(self, textvariable=self._cursor_hex_val, anchor="w", justify="left")

        self._cursor_xy.grid(row=8, column=0, padx=8, pady=(0, 2), sticky="ew")
        self._cursor_rgba.grid(row=9, column=0, padx=8, pady=(0, 2), sticky="ew")
        self._cursor_hex.grid(row=10, column=0, padx=8, pady=(0, 2), sticky="ew")

        # filler
        self.grid_rowconfigure(99, weight=1)

        # Compare / Processing
        # Обработка (в сайдбаре)
        self._proc_title = ctk.CTkLabel(self, text="Обработка", font=ctk.CTkFont(size=16, weight="bold"))
        self._proc_title.grid(row=20, column=0, padx=8, pady=(8, 4), sticky="w")

        self._processing_mode = ctk.StringVar(value="Нет")
        self._processing_menu = ctk.CTkOptionMenu(
            self,
            values=["Нет", "Оттенки серого"],
            variable=self._processing_mode,
            command=self._emit_processing_change,
        )
        self._processing_menu.grid(row=21, column=0, padx=8, pady=(0, 8), sticky="ew")

        self._compare_title = ctk.CTkLabel(self, text="Сравнение (внизу)", font=ctk.CTkFont(size=16, weight="bold"))
        self._compare_title.grid_remove()

        self._compare_mode = ctk.StringVar(value="Нет")
        self._compare_menu = ctk.CTkOptionMenu(self, values=["Нет", "Шторка", "2-up"], command=self._emit_compare_mode_change)
        self._compare_menu.grid_remove()

        self._wipe_label = ctk.CTkLabel(self, text="Позиция шторки")
        self._wipe_value = ctk.StringVar(value="50%")
        self._wipe_slider = ctk.CTkSlider(self, from_=0, to=100, number_of_steps=100, command=self._on_wipe_slider)
        self._wipe_slider.set(50)
        self._wipe_value_label = ctk.CTkLabel(self, textvariable=self._wipe_value)
        self._toggle_wipe_controls(visible=False)

    # ---- Public API ----
    def set_image_info(self, image_data: ImageData) -> None:
        self._path_val.set(str(image_data.path))
        self._size_val.set(self._format_size(image_data.size_bytes))
        self._dims_val.set(f"{image_data.width} × {image_data.height} px")
        self._mode_val.set(image_data.mode)

    def update_cursor_info(self, x: Optional[int], y: Optional[int], rgba: Optional[Tuple[int, int, int, int]]) -> None:
        if x is None or y is None or rgba is None:
            self._cursor_xy_val.set("—")
            self._cursor_rgba_val.set("—")
            self._cursor_hex_val.set("—")
            return
        self._cursor_xy_val.set(f"({x}, {y})")
        r, g, b, a = rgba
        self._cursor_rgba_val.set(f"RGBA: {r}, {g}, {b}, {a}")
        self._cursor_hex_val.set(f"HEX: {_rgba_to_hex(rgba)}")

    def set_zoom_percent(self, zoom_percent: int) -> None:
        self._zoom_slider.set(zoom_percent)
        self._zoom_value.set(f"{zoom_percent}%")

    def set_compare_mode_value(self, mode: str) -> None:
        # mode: "Нет" | "Шторка" | "2-up"
        self._compare_mode.set(mode)
        self._toggle_wipe_controls(visible=(mode == "Шторка"))

    def set_wipe_percent(self, percent: int) -> None:
        self._wipe_slider.set(percent)
        self._wipe_value.set(f"{percent}%")

    def set_processing_mode_value(self, mode: str) -> None:
        # mode: "Нет" | "Оттенки серого"
        self._processing_mode.set(mode)

    # ---- Events ----
    def _emit_open_file(self) -> None:
        if self.on_open_file:
            self.on_open_file()

    def _on_slider_change(self, value: float) -> None:
        zoom = int(round(value))
        self._zoom_value.set(f"{zoom}%")
        if self.on_zoom_change:
            self.on_zoom_change(zoom)

    def _emit_compare_mode_change(self, _value: str) -> None:
        mode = self._compare_mode.get()
        self._toggle_wipe_controls(visible=(mode == "Шторка"))
        if self.on_compare_mode_change:
            self.on_compare_mode_change(mode)

    def _on_wipe_slider(self, value: float) -> None:
        percent = int(round(value))
        self._wipe_value.set(f"{percent}%")
        if self.on_wipe_change:
            self.on_wipe_change(percent)

    def _emit_processing_change(self, _value: str) -> None:
        mode = self._processing_mode.get()
        if self.on_processing_change:
            self.on_processing_change(mode)

    # ---- Helpers ----
    def _format_size(self, size_bytes: Optional[int]) -> str:
        if size_bytes is None:
            return "—"
        thresholds = [("Б", 1024), ("КБ", 1024**2), ("МБ", 1024**3), ("ГБ", 1024**4)]
        for label, limit in thresholds:
            if size_bytes < limit:
                if label == "Б":
                    return f"{size_bytes} {label}"
                value = size_bytes / (limit // 1024)
                return f"{value:.1f} {label}"
        value = size_bytes / (1024**4)
        return f"{value:.1f} ГБ"

    def _toggle_wipe_controls(self, visible: bool) -> None:
        if visible:
            self._wipe_label.grid(row=24, column=0, padx=8, pady=(0, 4), sticky="w")
            self._wipe_slider.grid(row=25, column=0, padx=8, pady=(0, 4), sticky="ew")
            self._wipe_value_label.grid(row=26, column=0, padx=8, pady=(0, 8), sticky="w")
        else:
            self._wipe_label.grid_remove()
            self._wipe_slider.grid_remove()
            self._wipe_value_label.grid_remove()


