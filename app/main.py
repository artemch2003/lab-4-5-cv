"""Точка входа в приложение."""
from app.app import ImageInspectorApp


def main() -> None:
    """Создаёт и запускает главное окно приложения."""
    app = ImageInspectorApp()
    app.mainloop()


if __name__ == "__main__":
    main()


