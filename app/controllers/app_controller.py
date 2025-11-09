from __future__ import annotations

from dataclasses import dataclass
from tkinter import filedialog, TclError
from typing import Callable, Optional, Tuple

import customtkinter as ctk

from app.models.image_model import ImageData
from app.services.image_service import ImageService
from app.services.process_service import ProcessService
from app.ui.image_viewer import ImageViewer
from app.ui.sidebar import Sidebar
from app.ui.bottom_bar import BottomBar


@dataclass
class AppController:
    viewer: ImageViewer
    sidebar: Sidebar
    bottom: BottomBar
    window: ctk.CTk

    _image_service: ImageService = ImageService()
    _process_service: ProcessService = ProcessService()
    _current_image: Optional[ImageData] = None
    _processing_mode: str = "Нет"  # "Нет" | "Оттенки серого"

    def bind_events(self) -> None:
        self.sidebar.on_open_file = self._handle_open_file
        # Sidebar controls теперь скрыты; зум и сравнение — снизу
        self.viewer.on_cursor_move = self._handle_cursor_move
        self.viewer.on_zoom_change = self._handle_viewer_zoom_changed

        # Bottom bar bindings
        self.bottom.on_zoom_change = self._handle_zoom_change
        self.bottom.on_zoom_preset = self._handle_zoom_preset
        self.bottom.on_zoom_fit = self._handle_zoom_fit
        self.bottom.on_compare_mode_change = self._handle_compare_mode_change
        self.bottom.on_wipe_change = self._handle_wipe_change

        # Processing — в сайдбаре
        self.sidebar.on_processing_change = self._handle_processing_change

    # ---- Handlers ----
    def _handle_open_file(self) -> None:
        try:
            file_path = filedialog.askopenfilename(
                title="Выберите изображение",
                filetypes=(
                    ("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"),
                    ("All files", "*.*"),
                ),
            )
        except TclError:
            # Silent fail if dialog cannot open
            return

        if not file_path:
            return

        image_data = self._image_service.load_image(file_path)
        self._current_image = image_data

        self.viewer.set_image(image_data.pil_image)
        # apply processing if needed
        self._apply_processing()
        self.sidebar.set_image_info(image_data)
        # Reset zoom to fit
        self.viewer.set_zoom_to_fit()
        current_zoom = self.viewer.get_zoom_percent()
        self.bottom.set_zoom_percent(current_zoom)
        self.sidebar.set_zoom_percent(current_zoom)  # may be hidden
        # sync processing selector in sidebar
        self.sidebar.set_processing_mode_value(self._processing_mode)

    def _handle_zoom_change(self, zoom_percent: int) -> None:
        self.viewer.set_zoom_percent(zoom_percent)

    def _handle_cursor_move(self, x: Optional[int], y: Optional[int], rgba: Optional[Tuple[int, int, int, int]]) -> None:
        self.sidebar.update_cursor_info(x, y, rgba)

    def _handle_viewer_zoom_changed(self, zoom_percent: int) -> None:
        # Sync sidebar slider/value when user zooms with mouse wheel
        self.sidebar.set_zoom_percent(zoom_percent)
        self.bottom.set_zoom_percent(zoom_percent)

    def _handle_compare_mode_change(self, mode: str) -> None:
        self.viewer.set_compare_mode(mode)
        # Sidebar controls visibility handled inside Sidebar itself

    def _handle_wipe_change(self, percent: int) -> None:
        self.viewer.set_wipe_percent(percent)

    def _handle_processing_change(self, mode: str) -> None:
        self._processing_mode = mode
        self._apply_processing()

    def _handle_zoom_preset(self, zoom_percent: int) -> None:
        self.viewer.set_zoom_percent(zoom_percent)

    def _handle_zoom_fit(self) -> None:
        self.viewer.set_zoom_to_fit()
        current_zoom = self.viewer.get_zoom_percent()
        self.bottom.set_zoom_percent(current_zoom)
        self.sidebar.set_zoom_percent(current_zoom)

    # ---- Helpers ----
    def _apply_processing(self) -> None:
        if self._current_image is None:
            return
        if self._processing_mode == "Оттенки серого":
            processed = self._process_service.to_grayscale(self._current_image.pil_image)
            self.viewer.set_processed_image(processed)
        else:
            self.viewer.set_processed_image(None)


