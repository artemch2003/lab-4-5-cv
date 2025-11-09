from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk


class BottomBar(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, height=64, **kwargs)

        # callbacks
        self.on_zoom_change: Optional[Callable[[int], None]] = None
        self.on_zoom_preset: Optional[Callable[[int], None]] = None
        self.on_zoom_fit: Optional[Callable[[], None]] = None
        self.on_compare_mode_change: Optional[Callable[[str], None]] = None
        self.on_wipe_change: Optional[Callable[[int], None]] = None

        # layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)  # slider stretches
        self.grid_columnconfigure(5, weight=0)

        # Zoom controls
        self._zoom_label = ctk.CTkLabel(self, text="Масштаб")
        self._zoom_label.grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        self._zoom_value = ctk.StringVar(value="100%")
        self._zoom_slider = ctk.CTkSlider(self, from_=10, to=400, number_of_steps=390, command=self._on_slider_change)
        self._zoom_slider.set(100)
        self._zoom_slider.grid(row=0, column=1, padx=6, pady=8, sticky="ew")
        self._zoom_value_label = ctk.CTkLabel(self, textvariable=self._zoom_value, width=48, anchor="w")
        self._zoom_value_label.grid(row=0, column=2, padx=(6, 12), pady=8, sticky="w")

        # Presets + Fit
        self._preset_buttons = ctk.CTkSegmentedButton(
            self,
            values=["Fit", "25%", "50%", "100%", "200%", "400%"],
            command=self._on_preset_click,
        )
        self._preset_buttons.set("100%")
        self._preset_buttons.grid(row=0, column=3, padx=6, pady=8, sticky="w")

        # Compare
        self._compare_menu = ctk.CTkOptionMenu(
            self, values=["Нет", "Шторка", "2-up"], command=self._on_compare_mode
        )
        self._compare_menu.set("Нет")
        self._compare_menu.grid(row=0, column=4, padx=6, pady=8, sticky="w")

        # Wipe slider (hidden by default)
        self._wipe_value = ctk.StringVar(value="50%")
        self._wipe_slider = ctk.CTkSlider(self, from_=0, to=100, number_of_steps=100, command=self._on_wipe_slider)
        self._wipe_slider.set(50)
        self._wipe_value_label = ctk.CTkLabel(self, textvariable=self._wipe_value, width=40, anchor="w")
        self._toggle_wipe_controls(visible=False)

    # public API (sync from controller)
    def set_zoom_percent(self, percent: int) -> None:
        self._zoom_slider.set(percent)
        self._zoom_value.set(f"{percent}%")
        label = "Fit" if self._preset_buttons.get() == "Fit" else f"{percent}%"
        # keep segmented selection meaningful but don't force exact match
        if percent in (25, 50, 100, 200, 400):
            self._preset_buttons.set(f"{percent}%")
        else:
            # leave current, unless it shows stale numeric value
            cur = self._preset_buttons.get()
            if cur.endswith("%") and cur != f"{percent}%":
                self._preset_buttons.set(f"{percent}%")

    def set_compare_mode_value(self, mode: str) -> None:
        # "Нет" | "Шторка" | "2-up"
        self._compare_menu.set(mode)
        self._toggle_wipe_controls(visible=(mode == "Шторка"))

    def set_wipe_percent(self, percent: int) -> None:
        self._wipe_slider.set(percent)
        self._wipe_value.set(f"{percent}%")

    # events
    def _on_slider_change(self, value: float) -> None:
        percent = int(round(value))
        self._zoom_value.set(f"{percent}%")
        if self.on_zoom_change:
            self.on_zoom_change(percent)

    def _on_preset_click(self, value: str) -> None:
        if value == "Fit":
            if self.on_zoom_fit:
                self.on_zoom_fit()
            return
        if value.endswith("%"):
            try:
                percent = int(value[:-1])
            except ValueError:
                return
            if self.on_zoom_preset:
                self.on_zoom_preset(percent)

    def _on_compare_mode(self, value: str) -> None:
        self._toggle_wipe_controls(visible=(value == "Шторка"))
        if self.on_compare_mode_change:
            self.on_compare_mode_change(value)

    def _on_wipe_slider(self, value: float) -> None:
        percent = int(round(value))
        self._wipe_value.set(f"{percent}%")
        if self.on_wipe_change:
            self.on_wipe_change(percent)

    # helpers
    def _toggle_wipe_controls(self, visible: bool) -> None:
        if visible:
            self._wipe_slider.grid(row=0, column=5, padx=6, pady=8, sticky="ew")
            self._wipe_value_label.grid(row=0, column=6, padx=(0, 6), pady=8, sticky="w")
        else:
            self._wipe_slider.grid_remove()
            self._wipe_value_label.grid_remove()

