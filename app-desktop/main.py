import sys
import os
from PySide6.QtWidgets import QApplication
from services.config_service import ConfigService
from gui.login_window import LoginWindow


def load_styles():
    """Cargar estilos desde styles.qss"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        styles_path = os.path.join(current_dir, "styles.qss")

        with open(styles_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        return ""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SEMEFO Desktop")

    # Cargar estilos globales
    stylesheet = load_styles()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Crear el config_service
    config_service = ConfigService("config.json")

    if not config_service.load_config():
        config_service.create_default_config()

    # Crear y mostrar la ventana principal
    login_window = LoginWindow(config_service)
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
