"""Контроллер приложения: оркестрация UI и сервисов.

SOLID:
- SRP: класс управляет связями между UI и сервисами (без логики обработки изображений).
- DIP: зависит от сервисов как от абстрактных ролей; конкретные реализации инкапсулированы.
Clean Code:
- Обработчики компактны; тяжёлая логика вынесена в сервисы.
"""
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
    """Связывает элементы UI с прикладной логикой.

    Ответственности:
    - Инициализация и бинд событий (UI -> контроллер).
    - Загрузка изображений через `ImageService`.
    - Применение выбранной пользователем обработки через `ProcessService`.
    - Синхронизация состояния зума и режимов сравнения.
    """
    viewer: ImageViewer
    sidebar: Sidebar
    bottom: BottomBar
    window: ctk.CTk

    _image_service: ImageService = ImageService()
    _process_service: ProcessService = ProcessService()
    _current_image: Optional[ImageData] = None
    _processing_mode: str = "Нет"  # "Нет" | "Оттенки серого"

    def bind_events(self) -> None:
        """Регистрирует обработчики событий между UI-компонентами.

        Сохраняет слабую связность: компоненты UI ничего не знают друг о друге,
        общаются через контроллер.
        """
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
        """Применяет выбранный режим обработки к текущему изображению.

        Использует значения из UI (сайдбар) как параметры и делегирует расчёты
        методу сервиса обработки. Не мутирует исходное изображение.
        """
        if self._current_image is None:
            return
        src = self._current_image.pil_image
        mode = self._processing_mode
        processed = None
        if mode == "Оттенки серого":
            processed = self._process_service.to_grayscale(src)
        elif mode == "Края (Собель)":
            processed = self._process_service.segment_edges_sobel(src)
        elif mode == "Порог (P-tile)":
            # получить P из UI (0..1)
            p = 0.30
            try:
                p = self.sidebar.get_ptile_p()
            except Exception:
                pass
            processed = self._process_service.threshold_ptile(src, p=p)
        elif mode == "Порог (итеративный)":
            tol, mi = 0.5, 100
            try:
                tol, mi = self.sidebar.get_iterative_params()
            except Exception:
                pass
            processed = self._process_service.threshold_iterative(src, tol=tol, max_iter=mi)
        elif mode == "K-средних (k=2)":
            k, mi = 2, 50
            try:
                k, mi = self.sidebar.get_kmeans_single_params()
            except Exception:
                pass
            processed = self._process_service.kmeans_segment(src, k=k, max_iter=mi)
        elif mode == "K-средних (k=3)":
            k, mi = 3, 50
            try:
                k, mi = self.sidebar.get_kmeans_single_params()
            except Exception:
                pass
            processed = self._process_service.kmeans_segment(src, k=k, max_iter=mi)
        elif mode == "K-средних (k=4)":
            k, mi = 4, 50
            try:
                k, mi = self.sidebar.get_kmeans_single_params()
            except Exception:
                pass
            processed = self._process_service.kmeans_segment(src, k=k, max_iter=mi)
        elif mode == "K-средних сравнение (2,3,4)":
            ks = (2, 3, 4)
            try:
                ks = self.sidebar.get_kmeans_compare_ks()
            except Exception:
                pass
            processed = self._process_service.kmeans_compare(src, ks=ks)
        elif mode == "Порог (адаптивный)":
            # параметры: k, C, T, stat, polarity?
            k, C, T, stat, polarity = 15, 1.0, 0.0, "mean", "bright"
            try:
                k, C, T, stat, polarity = self.sidebar.get_adaptive_params()
            except Exception:
                pass
            processed = self._process_service.adaptive_threshold(src, k=k, C=C, T=T, stat=stat, polarity=polarity)
        elif mode == "Адаптивный сравнение (k)":
            ks = (3, 5, 9, 15)
            C, T, stat, polarity = 1.0, 0.0, "mean", "bright"
            try:
                # используем общие параметры адаптивного порога и список ks
                _k, C, T, stat, polarity = self.sidebar.get_adaptive_params()
                ks = self.sidebar.get_adaptive_compare_ks()
            except Exception:
                pass
            processed = self._process_service.adaptive_compare_k(src, ks=ks, C=C, T=T, stat=stat, polarity=polarity)
        elif mode == "Адаптивный сравнение (C)":
            Cs = (0.8, 1.0, 1.2)
            k, T, stat, polarity = 15, 0.0, "mean", "bright"
            try:
                k, _C, T, stat, polarity = self.sidebar.get_adaptive_params()
                Cs = self.sidebar.get_adaptive_compare_Cs()
            except Exception:
                pass
            processed = self._process_service.adaptive_compare_C(src, Cs=Cs, k=k, T=T, stat=stat, polarity=polarity)
        elif mode == "Адаптивный сравнение (T)":
            Ts = (-10.0, 0.0, 10.0)
            k, C, stat, polarity = 15, 1.0, "mean", "bright"
            try:
                k, C, _T, stat, polarity = self.sidebar.get_adaptive_params()
                Ts = self.sidebar.get_adaptive_compare_Ts()
            except Exception:
                pass
            processed = self._process_service.adaptive_compare_T(src, Ts=Ts, k=k, C=C, stat=stat, polarity=polarity)

        self.viewer.set_processed_image(processed)


