from __future__ import annotations

from dataclasses import dataclass
from tkinter import filedialog, TclError
from typing import Callable, Optional, Tuple

import customtkinter as ctk

from app.models.image_model import ImageData
from app.services.image_service import ImageService
from app.ui.image_viewer import ImageViewer
from app.ui.sidebar import Sidebar


@dataclass
class AppController:
    viewer: ImageViewer
    sidebar: Sidebar
    window: ctk.CTk

    _image_service: ImageService = ImageService()
    _current_image: Optional[ImageData] = None

    def bind_events(self) -> None:
        self.sidebar.on_open_file = self._handle_open_file
        self.sidebar.on_zoom_change = self._handle_zoom_change
        self.viewer.on_cursor_move = self._handle_cursor_move
        self.viewer.on_zoom_change = self._handle_viewer_zoom_changed

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
        self.sidebar.set_image_info(image_data)
        # Reset zoom to fit
        self.viewer.set_zoom_to_fit()
        self.sidebar.set_zoom_percent(self.viewer.get_zoom_percent())

    def _handle_zoom_change(self, zoom_percent: int) -> None:
        self.viewer.set_zoom_percent(zoom_percent)

    def _handle_cursor_move(self, x: Optional[int], y: Optional[int], rgba: Optional[Tuple[int, int, int, int]]) -> None:
        self.sidebar.update_cursor_info(x, y, rgba)

    def _handle_viewer_zoom_changed(self, zoom_percent: int) -> None:
        # Sync sidebar slider/value when user zooms with mouse wheel
        self.sidebar.set_zoom_percent(zoom_percent)


