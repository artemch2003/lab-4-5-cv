import customtkinter as ctk

from app.controllers.app_controller import AppController
from app.ui.image_viewer import ImageViewer
from app.ui.sidebar import Sidebar
from app.ui.bottom_bar import BottomBar


class ImageInspectorApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("Image Inspector")
        self.minsize(900, 600)

        # root layout: left viewer, right sidebar
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._viewer = ImageViewer(self)
        self._viewer.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=(12, 6))

        self._sidebar = Sidebar(self)
        self._sidebar.grid(row=0, column=1, sticky="ns", padx=(6, 12), pady=(12, 6))

        self._bottom = BottomBar(self)
        self._bottom.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))

        self._controller = AppController(viewer=self._viewer, sidebar=self._sidebar, bottom=self._bottom, window=self)
        self._controller.bind_events()


