from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import logging
from services.utils import load_stylesheet

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class HeaderWidget(QWidget):
    def __init__(self, medico_nombre, numero_expediente="", nombre_sesion="", config_service=None):
        super().__init__()
        self.medico_nombre = medico_nombre
        self.numero_expediente = numero_expediente
        self.nombre_sesion = nombre_sesion
        self.config_service = config_service
        self.init_ui()

    def init_ui(self):
        # ALTURA FIJA para consistencia en todas las pantallas
        self.setFixedHeight(100)
        self.setStyleSheet(
            "background-color: #f8f9fa; border-bottom: 1px solid #dee2e6;")

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 10, 20, 10)  # Márgenes fijos
        header_layout.setAlignment(Qt.AlignVCenter)

        # Logo con tamaño fijo
        logo_label = QLabel()
        try:
            logo_pixmap = QPixmap("logo.png").scaledToHeight(
                80, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        except:
            logo_label.setText("LOGO")
            logo_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Información de expediente y sesión (centrada)
        if self.numero_expediente and self.nombre_sesion:
            texto_central = f"Expediente #{self.numero_expediente}<br>Sesión: {self.nombre_sesion}"
        else:
            texto_central = ""
        self.expediente_sesion_label = QLabel(texto_central)
        self.expediente_sesion_label.setAlignment(Qt.AlignCenter)
        self.expediente_sesion_label.setTextFormat(Qt.RichText)
        self.expediente_sesion_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #333;")

        # Información del médico y botón de salir (derecha)
        medico_label = QLabel(f"Hola {self.medico_nombre}")
        medico_label.setStyleSheet("font-size: 14px; color: #333;")

        logout_button = QPushButton("Salir")
        logout_button.setProperty("class", "logout-button")
        logout_button.setFixedSize(80, 35)  # Tamaño consistente
        logout_button.setToolTip("Cerrar sesión")
        logout_button.clicked.connect(self.logout)

        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_layout.setSpacing(5)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(medico_label)
        right_layout.addWidget(logout_button)

        # Layout del header con proporciones fijas
        header_layout.addWidget(logo_label, 1)           # 1/4 del espacio
        header_layout.addWidget(
            self.expediente_sesion_label, 2)  # 2/4 del espacio
        header_layout.addLayout(right_layout, 1)         # 1/4 del espacio

        self.setLayout(header_layout)
        load_stylesheet(self)

    def update_expediente_info(self, numero_expediente, nombre_sesion):
        """Actualizar información del expediente sin recrear el header"""
        self.numero_expediente = numero_expediente
        self.nombre_sesion = nombre_sesion

        if numero_expediente and nombre_sesion:
            texto_central = f"Expediente #{numero_expediente}<br>Sesión: {nombre_sesion}"
        else:
            texto_central = ""

        self.expediente_sesion_label.setText(texto_central)

    def logout(self):
        from gui.login_window import LoginWindow
        try:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Cerrar Sesión")
            msg_box.setText(
                f"¿Está seguro que desea cerrar la sesión de {self.medico_nombre}?")
            msg_box.setIcon(QMessageBox.Question)

            yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
            yes_button.setProperty("class", "action-button")

            no_button = msg_box.addButton("No", QMessageBox.NoRole)
            no_button.setProperty("class", "cancel-button")

            msg_box.setDefaultButton(no_button)
            load_stylesheet(msg_box)

            reply = msg_box.exec()

            if msg_box.clickedButton() == yes_button:
                logging.info(
                    f"Usuario {self.medico_nombre} cerró sesión desde Header.")
                self.login_window = LoginWindow(self.config_service)
                self.login_window.show()
                self.window().close()

        except Exception as e:
            logging.error(f"Error en logout: {e}")
            QMessageBox.critical(
                self, "Error", f"Error al cerrar sesión: {str(e)}")
