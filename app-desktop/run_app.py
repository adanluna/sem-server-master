
from PySide6.QtWidgets import QApplication
from services.config_service import ConfigService
from gui.login_window import LoginWindow
import sys

def main():
    app = QApplication(sys.argv)

    # Crear el config_service (sin encriptación)
    config_service = ConfigService("config.json")

    # Verificar si existe configuración, si no crear una por defecto
    if not config_service.load_config():
        print("🔧 Creando archivo de configuración por defecto...")
        config_service.create_default_config()

    # Pasar el config_service a LoginWindow
    login_window = LoginWindow(config_service)
    login_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
