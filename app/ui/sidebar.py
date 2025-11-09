"""Боковая панель: открытие файла, информация, параметры алгоритмов обработки.

Принципы:
- SRP: управляет только UI параметров, не содержит алгоритмов.
- ISP: выдаёт параметры через компактные методы `get_*`, события через `on_*`.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import customtkinter as ctk

from app.models.image_model import ImageData


def _rgba_to_hex(rgba: Tuple[int, int, int, int]) -> str:
    """Преобразует RGBA в HEX (без альфа)."""
    r, g, b, _a = rgba
    return f"#{r:02X}{g:02X}{b:02X}"


class Sidebar(ctk.CTkFrame):
    """Панель инструментов с блоками: файл, информация, курсор, обработка."""
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
        # Вкладки режимов обработки
        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=21, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self._tabs.add("Базовая")
        self._tabs.add("Границы")
        self._tabs.add("Пороговые")
        self._tabs.add("K-средних")
        # позволим вкладкам занимать доступную высоту
        self.grid_rowconfigure(21, weight=1)

        # Кнопка быстрого возврата к оригиналу
        self._reset_btn = ctk.CTkButton(self, text="Показать оригинал", command=self._reset_to_original)
        self._reset_btn.grid(row=22, column=0, padx=8, pady=(0, 8), sticky="ew")

        # Базовая
        base_tab = self._tabs.tab("Базовая")
        base_tab.grid_columnconfigure(0, weight=1)
        self._rb_none = ctk.CTkRadioButton(
            base_tab, text="Нет", variable=self._processing_mode, value="Нет", command=self._emit_processing_change
        )
        self._rb_gray = ctk.CTkRadioButton(
            base_tab,
            text="Оттенки серого",
            variable=self._processing_mode,
            value="Оттенки серого",
            command=self._emit_processing_change,
        )
        self._rb_none.grid(row=0, column=0, padx=6, pady=(4, 2), sticky="w")
        self._rb_gray.grid(row=1, column=0, padx=6, pady=(2, 4), sticky="w")

        # Границы
        edges_tab = self._tabs.tab("Границы")
        edges_tab.grid_columnconfigure(0, weight=1)
        self._rb_sobel = ctk.CTkRadioButton(
            edges_tab,
            text="Края (Собель)",
            variable=self._processing_mode,
            value="Края (Собель)",
            command=self._emit_processing_change,
        )
        self._rb_sobel.grid(row=0, column=0, padx=6, pady=(6, 6), sticky="w")

        # Пороговые
        # Внутри «Пороговые» используем прокручиваемый контейнер
        thr_container = self._tabs.tab("Пороговые")
        thr_container.grid_rowconfigure(0, weight=1)
        thr_container.grid_columnconfigure(0, weight=1)
        thr_tab = ctk.CTkScrollableFrame(thr_container)
        thr_tab.grid(row=0, column=0, sticky="nsew")
        thr_tab.grid_columnconfigure(0, weight=1)
        # P-tile
        self._rb_ptile = ctk.CTkRadioButton(
            thr_tab,
            text="Порог (P-tile)",
            variable=self._processing_mode,
            value="Порог (P-tile)",
            command=self._emit_processing_change,
        )
        self._rb_ptile.grid(row=0, column=0, padx=6, pady=(6, 2), sticky="w")
        self._ptile_p_val = ctk.StringVar(value="30%")
        self._ptile_p_label = ctk.CTkLabel(thr_tab, text="P (доля объекта):")
        self._ptile_p_slider = ctk.CTkSlider(thr_tab, from_=0, to=100, number_of_steps=100, command=self._on_ptile_change)
        self._ptile_p_slider.set(30)
        self._ptile_p_value = ctk.CTkLabel(thr_tab, textvariable=self._ptile_p_val, width=48, anchor="w")
        self._ptile_p_label.grid(row=1, column=0, padx=6, pady=(0, 2), sticky="w")
        self._ptile_p_slider.grid(row=2, column=0, padx=6, pady=(0, 2), sticky="ew")
        self._ptile_p_value.grid(row=3, column=0, padx=6, pady=(0, 6), sticky="w")
        # Итеративный
        self._rb_iter = ctk.CTkRadioButton(
            thr_tab,
            text="Порог (итеративный)",
            variable=self._processing_mode,
            value="Порог (итеративный)",
            command=self._emit_processing_change,
        )
        self._rb_iter.grid(row=4, column=0, padx=6, pady=(8, 2), sticky="w")
        self._iter_tol_val = ctk.StringVar(value="0.5")
        self._iter_tol_label = ctk.CTkLabel(thr_tab, text="Порог сходимости (tol):")
        self._iter_tol_slider = ctk.CTkSlider(thr_tab, from_=0.1, to=5.0, number_of_steps=49, command=self._on_iter_tol_change)
        self._iter_tol_slider.set(0.5)
        self._iter_tol_value = ctk.CTkLabel(thr_tab, textvariable=self._iter_tol_val, width=48, anchor="w")
        self._iter_tol_label.grid(row=5, column=0, padx=6, pady=(0, 2), sticky="w")
        self._iter_tol_slider.grid(row=6, column=0, padx=6, pady=(0, 2), sticky="ew")
        self._iter_tol_value.grid(row=7, column=0, padx=6, pady=(0, 4), sticky="w")
        self._iter_max_iter_val = ctk.StringVar(value="100")
        self._iter_max_iter_label = ctk.CTkLabel(thr_tab, text="Макс. итераций:")
        self._iter_max_iter_entry = ctk.CTkEntry(thr_tab, textvariable=self._iter_max_iter_val, width=80)
        self._iter_max_iter_label.grid(row=8, column=0, padx=6, pady=(0, 2), sticky="w")
        self._iter_max_iter_entry.grid(row=9, column=0, padx=6, pady=(0, 8), sticky="w")
        self._iter_max_iter_entry.bind("<FocusOut>", self._on_iter_params_commit)
        self._iter_max_iter_entry.bind("<Return>", self._on_iter_params_commit)
        # Адаптивный порог — одиночный
        self._rb_adapt = ctk.CTkRadioButton(
            thr_tab,
            text="Порог (адаптивный)",
            variable=self._processing_mode,
            value="Порог (адаптивный)",
            command=self._emit_processing_change,
        )
        self._rb_adapt.grid(row=10, column=0, padx=6, pady=(8, 2), sticky="w")

        self._adapt_k_val = ctk.StringVar(value="15")
        self._adapt_k_label = ctk.CTkLabel(thr_tab, text="Размер окна k (нечётн.):")
        self._adapt_k_slider = ctk.CTkSlider(thr_tab, from_=3, to=51, number_of_steps=48, command=self._on_adapt_k_change)
        self._adapt_k_slider.set(15)
        self._adapt_k_value = ctk.CTkLabel(thr_tab, textvariable=self._adapt_k_val, width=32, anchor="w")
        self._adapt_k_label.grid(row=11, column=0, padx=6, pady=(0, 2), sticky="w")
        self._adapt_k_slider.grid(row=12, column=0, padx=6, pady=(0, 2), sticky="ew")
        self._adapt_k_value.grid(row=13, column=0, padx=6, pady=(0, 4), sticky="w")

        self._adapt_C_val = ctk.StringVar(value="1.0")
        self._adapt_C_label = ctk.CTkLabel(thr_tab, text="Коэффициент C:")
        self._adapt_C_slider = ctk.CTkSlider(thr_tab, from_=0.0, to=2.0, number_of_steps=200, command=self._on_adapt_C_change)
        self._adapt_C_slider.set(1.0)
        self._adapt_C_value = ctk.CTkLabel(thr_tab, textvariable=self._adapt_C_val, width=48, anchor="w")
        self._adapt_C_label.grid(row=14, column=0, padx=6, pady=(0, 2), sticky="w")
        self._adapt_C_slider.grid(row=15, column=0, padx=6, pady=(0, 2), sticky="ew")
        self._adapt_C_value.grid(row=16, column=0, padx=6, pady=(0, 4), sticky="w")

        self._adapt_T_val = ctk.StringVar(value="0")
        self._adapt_T_label = ctk.CTkLabel(thr_tab, text="Смещение T:")
        self._adapt_T_slider = ctk.CTkSlider(thr_tab, from_=-50, to=50, number_of_steps=100, command=self._on_adapt_T_change)
        self._adapt_T_slider.set(0)
        self._adapt_T_value = ctk.CTkLabel(thr_tab, textvariable=self._adapt_T_val, width=48, anchor="w")
        self._adapt_T_label.grid(row=17, column=0, padx=6, pady=(0, 2), sticky="w")
        self._adapt_T_slider.grid(row=18, column=0, padx=6, pady=(0, 2), sticky="ew")
        self._adapt_T_value.grid(row=19, column=0, padx=6, pady=(0, 4), sticky="w")

        self._adapt_stat_label = ctk.CTkLabel(thr_tab, text="Статистика по окрестности:")
        self._adapt_stat_menu = ctk.CTkOptionMenu(
            thr_tab,
            values=["Среднее", "Медиана", "Полудиапазон (min+max)/2"],
            command=self._on_adapt_stat_change,
        )
        self._adapt_stat_menu.set("Среднее")
        self._adapt_stat_label.grid(row=20, column=0, padx=6, pady=(0, 2), sticky="w")
        self._adapt_stat_menu.grid(row=21, column=0, padx=6, pady=(0, 8), sticky="w")

        # Адаптивный порог — сравнение
        self._rb_adapt_cmp_k = ctk.CTkRadioButton(
            thr_tab,
            text="Адаптивный сравнение (k)",
            variable=self._processing_mode,
            value="Адаптивный сравнение (k)",
            command=self._emit_processing_change,
        )
        self._rb_adapt_cmp_k.grid(row=22, column=0, padx=6, pady=(8, 2), sticky="w")
        self._adapt_cmp_ks_label = ctk.CTkLabel(thr_tab, text="Список k (через запятую):")
        self._adapt_cmp_ks_vals = ctk.StringVar(value="3,5,9,15")
        self._adapt_cmp_ks_entry = ctk.CTkEntry(thr_tab, textvariable=self._adapt_cmp_ks_vals)
        self._adapt_cmp_ks_label.grid(row=23, column=0, padx=6, pady=(0, 2), sticky="w")
        self._adapt_cmp_ks_entry.grid(row=24, column=0, padx=6, pady=(0, 4), sticky="ew")
        self._adapt_cmp_ks_entry.bind("<FocusOut>", self._on_adapt_params_commit)
        self._adapt_cmp_ks_entry.bind("<Return>", self._on_adapt_params_commit)

        self._rb_adapt_cmp_c = ctk.CTkRadioButton(
            thr_tab,
            text="Адаптивный сравнение (C)",
            variable=self._processing_mode,
            value="Адаптивный сравнение (C)",
            command=self._emit_processing_change,
        )
        self._rb_adapt_cmp_c.grid(row=25, column=0, padx=6, pady=(8, 2), sticky="w")
        self._adapt_cmp_cs_label = ctk.CTkLabel(thr_tab, text="Список C (через запятую):")
        self._adapt_cmp_cs_vals = ctk.StringVar(value="0.8,1.0,1.2")
        self._adapt_cmp_cs_entry = ctk.CTkEntry(thr_tab, textvariable=self._adapt_cmp_cs_vals)
        self._adapt_cmp_cs_label.grid(row=26, column=0, padx=6, pady=(0, 2), sticky="w")
        self._adapt_cmp_cs_entry.grid(row=27, column=0, padx=6, pady=(0, 4), sticky="ew")
        self._adapt_cmp_cs_entry.bind("<FocusOut>", self._on_adapt_params_commit)
        self._adapt_cmp_cs_entry.bind("<Return>", self._on_adapt_params_commit)

        self._rb_adapt_cmp_t = ctk.CTkRadioButton(
            thr_tab,
            text="Адаптивный сравнение (T)",
            variable=self._processing_mode,
            value="Адаптивный сравнение (T)",
            command=self._emit_processing_change,
        )
        self._rb_adapt_cmp_t.grid(row=28, column=0, padx=6, pady=(8, 2), sticky="w")
        self._adapt_cmp_ts_label = ctk.CTkLabel(thr_tab, text="Список T (через запятую):")
        self._adapt_cmp_ts_vals = ctk.StringVar(value="-10,0,10")
        self._adapt_cmp_ts_entry = ctk.CTkEntry(thr_tab, textvariable=self._adapt_cmp_ts_vals)
        self._adapt_cmp_ts_label.grid(row=29, column=0, padx=6, pady=(0, 2), sticky="w")
        self._adapt_cmp_ts_entry.grid(row=30, column=0, padx=6, pady=(0, 10), sticky="ew")
        self._adapt_cmp_ts_entry.bind("<FocusOut>", self._on_adapt_params_commit)
        self._adapt_cmp_ts_entry.bind("<Return>", self._on_adapt_params_commit)

        # K-средних
        km_tab = self._tabs.tab("K-средних")
        km_tab.grid_columnconfigure(0, weight=1)
        self._rb_kmeans_single = ctk.CTkRadioButton(
            km_tab,
            text="K‑средних (k)",
            variable=self._processing_mode,
            value="K-средних (k=2)",
            command=self._emit_processing_change,
        )
        self._rb_kmeans_single.grid(row=0, column=0, padx=6, pady=(6, 2), sticky="w")
        self._kmeans_k_val = ctk.StringVar(value="2")
        self._kmeans_k_label = ctk.CTkLabel(km_tab, text="k:")
        self._kmeans_k_slider = ctk.CTkSlider(km_tab, from_=2, to=8, number_of_steps=6, command=self._on_kmeans_k_change)
        self._kmeans_k_slider.set(2)
        self._kmeans_k_value = ctk.CTkLabel(km_tab, textvariable=self._kmeans_k_val, width=32, anchor="w")
        self._kmeans_k_label.grid(row=1, column=0, padx=6, pady=(0, 2), sticky="w")
        self._kmeans_k_slider.grid(row=2, column=0, padx=6, pady=(0, 2), sticky="ew")
        self._kmeans_k_value.grid(row=3, column=0, padx=6, pady=(0, 8), sticky="w")
        self._kmeans_max_iter_val = ctk.StringVar(value="50")
        self._kmeans_max_iter_label = ctk.CTkLabel(km_tab, text="Макс. итераций:")
        self._kmeans_max_iter_entry = ctk.CTkEntry(km_tab, textvariable=self._kmeans_max_iter_val, width=80)
        self._kmeans_max_iter_label.grid(row=4, column=0, padx=6, pady=(0, 2), sticky="w")
        self._kmeans_max_iter_entry.grid(row=5, column=0, padx=6, pady=(0, 8), sticky="w")
        self._kmeans_max_iter_entry.bind("<FocusOut>", self._on_kmeans_params_commit)
        self._kmeans_max_iter_entry.bind("<Return>", self._on_kmeans_params_commit)
        self._rb_kmeans_cmp = ctk.CTkRadioButton(
            km_tab,
            text="K‑средних сравнение",
            variable=self._processing_mode,
            value="K-средних сравнение (2,3,4)",
            command=self._emit_processing_change,
        )
        self._rb_kmeans_cmp.grid(row=6, column=0, padx=6, pady=(8, 2), sticky="w")
        self._kmeans_cmp_label = ctk.CTkLabel(km_tab, text="Список k (через запятую):")
        self._kmeans_cmp_vals = ctk.StringVar(value="2,3,4")
        self._kmeans_cmp_entry = ctk.CTkEntry(km_tab, textvariable=self._kmeans_cmp_vals)
        self._kmeans_cmp_label.grid(row=7, column=0, padx=6, pady=(0, 2), sticky="w")
        self._kmeans_cmp_entry.grid(row=8, column=0, padx=6, pady=(0, 8), sticky="ew")
        self._kmeans_cmp_entry.bind("<FocusOut>", self._on_kmeans_params_commit)
        self._kmeans_cmp_entry.bind("<Return>", self._on_kmeans_params_commit)

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
        """Отображает метаданные загруженного изображения."""
        self._path_val.set(str(image_data.path))
        self._size_val.set(self._format_size(image_data.size_bytes))
        self._dims_val.set(f"{image_data.width} × {image_data.height} px")
        self._mode_val.set(image_data.mode)

    def update_cursor_info(self, x: Optional[int], y: Optional[int], rgba: Optional[Tuple[int, int, int, int]]) -> None:
        """Обновляет информацию по курсору (координаты, RGBA, HEX)."""
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
        """Синхронизирует скрытый слайдер масштаба (историческая совместимость)."""
        self._zoom_slider.set(zoom_percent)
        self._zoom_value.set(f"{zoom_percent}%")

    def set_compare_mode_value(self, mode: str) -> None:
        """Синхронизирует (скрытый) режим сравнения и «шторки»."""
        # mode: "Нет" | "Шторка" | "2-up"
        self._compare_mode.set(mode)
        self._toggle_wipe_controls(visible=(mode == "Шторка"))

    def set_wipe_percent(self, percent: int) -> None:
        """Синхронизирует положение «шторки» на сайдбаре (скрытые элементы)."""
        self._wipe_slider.set(percent)
        self._wipe_value.set(f"{percent}%")

    def set_processing_mode_value(self, mode: str) -> None:
        """Выставляет активный режим обработки и переключает вкладку."""
        # mode: "Нет" | "Оттенки серого" | другие режимы
        self._processing_mode.set(mode)
        # Переключим вкладку для удобства
        if mode in ("Нет", "Оттенки серого"):
            self._tabs.set("Базовая")
        elif mode.startswith("Края"):
            self._tabs.set("Границы")
        elif mode.startswith("Порог") or mode.startswith("Адаптивный"):
            self._tabs.set("Пороговые")
        elif mode.startswith("K-средних"):
            self._tabs.set("K-средних")

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

    def _emit_processing_change(self, _value: object | None = None) -> None:
        mode = self._processing_mode.get()
        if self.on_processing_change:
            self.on_processing_change(mode)

    # ---- Helpers ----
    # Параметры алгоритмов
    def get_ptile_p(self) -> float:
        """Возвращает P для P-tile в диапазоне [0,1]."""
        try:
            percent = float(self._ptile_p_slider.get())
        except Exception:
            percent = 30.0
        return max(0.0, min(1.0, percent / 100.0))

    def get_iterative_params(self) -> Tuple[float, int]:
        """Возвращает (tol, max_iter) для итеративного порога."""
        try:
            tol = float(self._iter_tol_slider.get())
        except Exception:
            tol = 0.5
        try:
            mi = int(self._iter_max_iter_val.get())
        except Exception:
            mi = 100
        mi = max(1, min(10000, mi))
        return tol, mi

    def get_kmeans_single_params(self) -> Tuple[int, int]:
        """Возвращает (k, max_iter) для одиночного K-средних."""
        try:
            k = int(round(self._kmeans_k_slider.get()))
        except Exception:
            k = 2
        k = max(2, min(64, k))
        try:
            mi = int(self._kmeans_max_iter_val.get())
        except Exception:
            mi = 50
        mi = max(1, min(10000, mi))
        return k, mi

    def get_kmeans_compare_ks(self) -> Tuple[int, ...]:
        """Возвращает кортеж k (>=2) для сравнения K-средних, не более 8 значений."""
        text = self._kmeans_cmp_vals.get().strip()
        parts = [p.strip() for p in text.split(",") if p.strip()]
        ks = []
        for p in parts:
            try:
                v = int(p)
                if v >= 2:
                    ks.append(v)
            except ValueError:
                continue
        if not ks:
            ks = [2, 3, 4]
        return tuple(ks[:8])
    # Адаптивный: параметры и списки для сравнения
    def get_adaptive_params(self) -> Tuple[int, float, float, str, str]:
        """Возвращает (k, C, T, stat, polarity) для адаптивного порогования.

        Где:
            k — нечётное, минимум 3;
            stat — 'mean' | 'median' | 'midrange';
            polarity — пока фиксировано 'bright' (объект светлее фона).
        """
        # k
        try:
            k_val = int(round(self._adapt_k_slider.get()))
        except Exception:
            k_val = 15
        if k_val < 3:
            k_val = 3
        if k_val % 2 == 0:
            k_val += 1
        # C
        try:
            C_val = float(self._adapt_C_slider.get())
        except Exception:
            C_val = 1.0
        # T
        try:
            T_val = float(self._adapt_T_slider.get())
        except Exception:
            T_val = 0.0
        # stat
        stat_text = self._adapt_stat_menu.get()
        if stat_text.startswith("Сред"):
            stat_key = "mean"
        elif stat_text.startswith("Мед"):
            stat_key = "median"
        else:
            stat_key = "midrange"
        # polarity — пока фиксируем bright (объект светлее)
        polarity = "bright"
        return k_val, C_val, T_val, stat_key, polarity

    def get_adaptive_compare_ks(self) -> Tuple[int, ...]:
        """Возвращает k (нечётные >=3) для сравнения по окну, не более 8 значений."""
        text = self._adapt_cmp_ks_vals.get().strip()
        parts = [p.strip() for p in text.split(",") if p.strip()]
        ks = []
        for p in parts:
            try:
                v = int(p)
                if v < 3:
                    continue
                if v % 2 == 0:
                    v += 1
                ks.append(v)
            except ValueError:
                continue
        if not ks:
            ks = [3, 5, 9, 15]
        return tuple(ks[:8])

    def get_adaptive_compare_Cs(self) -> Tuple[float, ...]:
        """Возвращает список значений C для сравнения, не более 8 значений."""
        text = self._adapt_cmp_cs_vals.get().strip()
        parts = [p.strip() for p in text.split(",") if p.strip()]
        out: list[float] = []
        for p in parts:
            try:
                out.append(float(p))
            except ValueError:
                continue
        if not out:
            out = [0.8, 1.0, 1.2]
        return tuple(out[:8])

    def get_adaptive_compare_Ts(self) -> Tuple[float, ...]:
        """Возвращает список значений T для сравнения, не более 8 значений."""
        text = self._adapt_cmp_ts_vals.get().strip()
        parts = [p.strip() for p in text.split(",") if p.strip()]
        out: list[float] = []
        for p in parts:
            try:
                out.append(float(p))
            except ValueError:
                continue
        if not out:
            out = [-10.0, 0.0, 10.0]
        return tuple(out[:8])

    # Обработчики изменения параметров — пересчитать немедленно
    def _on_ptile_change(self, value: float) -> None:
        self._ptile_p_val.set(f"{int(round(value))}%")
        if self._processing_mode.get() == "Порог (P-tile)":
            self._emit_processing_change("")

    def _on_iter_tol_change(self, value: float) -> None:
        self._iter_tol_val.set(f"{value:.1f}")
        if self._processing_mode.get() == "Порог (итеративный)":
            self._emit_processing_change("")

    def _on_iter_params_commit(self, _event: object) -> None:
        if self._processing_mode.get() == "Порог (итеративный)":
            self._emit_processing_change("")

    def _on_kmeans_k_change(self, value: float) -> None:
        self._kmeans_k_val.set(f"{int(round(value))}")
        if self._processing_mode.get().startswith("K-средних (k"):
            self._emit_processing_change("")

    def _on_kmeans_params_commit(self, _event: object) -> None:
        if self._processing_mode.get().startswith("K-средних"):
            self._emit_processing_change("")
    # Обработчики адаптивного — пересчитываем при изменении
    def _on_adapt_k_change(self, value: float) -> None:
        k = int(round(value))
        if k % 2 == 0:
            k += 1
        k = max(3, k)
        self._adapt_k_val.set(f"{k}")
        if self._processing_mode.get().startswith("Порог (адаптивный)"):
            self._emit_processing_change("")

    def _on_adapt_C_change(self, value: float) -> None:
        self._adapt_C_val.set(f"{value:.2f}")
        if self._processing_mode.get().startswith("Порог (адаптивный)"):
            self._emit_processing_change("")

    def _on_adapt_T_change(self, value: float) -> None:
        self._adapt_T_val.set(f"{int(round(value))}")
        if self._processing_mode.get().startswith("Порог (адаптивный)"):
            self._emit_processing_change("")

    def _on_adapt_stat_change(self, _value: str) -> None:
        if self._processing_mode.get().startswith("Порог (адаптивный)"):
            self._emit_processing_change("")

    def _on_adapt_params_commit(self, _event: object) -> None:
        mode = self._processing_mode.get()
        if mode.startswith("Адаптивный сравнение"):
            self._emit_processing_change("")

    def _reset_to_original(self) -> None:
        self._processing_mode.set("Нет")
        self._tabs.set("Базовая")
        if self.on_processing_change:
            self.on_processing_change("Нет")
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


