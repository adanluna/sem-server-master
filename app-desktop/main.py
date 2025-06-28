import sys
from PySide6.QtWidgets import QApplication
from gui.login_window import LoginWindow
from services.config_service import ConfigService
from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = b'rYrW0xe8EDb8w2oOjogW7m3AeExDHibOd7QEpKzK_lc='

    config_service = ConfigService(key)

    app = QApplication(sys.argv)
    window = LoginWindow(config_service)
    window.show()
    sys.exit(app.exec())
