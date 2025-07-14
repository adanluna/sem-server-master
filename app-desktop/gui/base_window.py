from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from services.utils import load_stylesheet
import logging


class BaseWindow(QWidget):
    def __init__(self, config_service=None, window_title="SEMEFO"):
        super().__init__()
        self.config_service = config_service
        self.setWindowTitle(window_title)
        self.resize(1024, 768)
        self.center_window()

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Contenido (será implementado por las subclases)
        self.content_widget = QWidget()
        main_layout.addWidget(self.content_widget)

        # Cargar estilos
        load_stylesheet(self)

    def center_window(self):
        """Centrar la ventana en la pantalla"""
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def logout(self):
        """Cerrar sesión y volver al login"""
        try:
            from gui.login_window import LoginWindow
            self.login_window = LoginWindow(self.config_service)
            self.login_window.show()
            self.close()
        except Exception as e:
            logging.error(f"Error en logout: {e}")


class BaseWindowWithHeader(BaseWindow):
    def __init__(self, medico_nombre="", numero_expediente="", nombre_sesion="", config_service=None, window_title="SEMEFO", hide_logout=False):  # ✅ Agregar hide_logout=False
        super().__init__(config_service, window_title)
        self.medico_nombre = medico_nombre
        self.numero_expediente = numero_expediente
        self.nombre_sesion = nombre_sesion
        self.hide_logout = hide_logout  # ✅ Agregar esta línea

        # Recrear layout principal para incluir header
        main_layout = self.layout()
        main_layout.removeWidget(self.content_widget)

        # Agregar header
        header_widget = self.create_header()
        main_layout.addWidget(header_widget)

        # Reagregar contenido
        main_layout.addWidget(self.content_widget)

    def create_header(self):
        header_widget = QWidget()
        header_widget.setFixedHeight(100)
        header_widget.setStyleSheet(
            "background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;")

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(20)

        # IZQUIERDA: Logo
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(
                60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_logo)
        else:
            logo_label.setText("LOGO")
            logo_label.setStyleSheet(
                "padding: 20px; font-weight: bold; color: #333;")  # Quitar "border:" solo

        logo_label.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(logo_label)

        header_layout.addLayout(logo_layout)

        # CENTRO: Información de expediente y sesión
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setSpacing(5)

        # Solo mostrar si tienen valores
        if self.numero_expediente:
            expediente_label = QLabel(f"Expediente: {self.numero_expediente}")
            expediente_label.setAlignment(Qt.AlignCenter)
            expediente_label.setStyleSheet(
                "font-weight: bold; font-size: 16px; color: #333;")
            center_layout.addWidget(expediente_label)

        if self.nombre_sesion:
            sesion_label = QLabel(f"Sesión: {self.nombre_sesion}")
            sesion_label.setAlignment(Qt.AlignCenter)
            sesion_label.setStyleSheet(
                "font-size: 14px; color: #666;")
            center_layout.addWidget(sesion_label)

        # Si no hay expediente ni sesión, agregar espaciador
        if not self.numero_expediente and not self.nombre_sesion:
            center_layout.addItem(QSpacerItem(
                20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        header_layout.addLayout(center_layout)

        # DERECHA: Usuario y botón logout
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setSpacing(8)

        # Nombre del usuario LDAP
        if self.medico_nombre:
            user_label = QLabel(self.medico_nombre)
            user_label.setAlignment(Qt.AlignCenter)
            user_label.setStyleSheet(
                "font-weight: bold; font-size: 14px; color: #333;")
            right_layout.addWidget(user_label)

        # ✅ Botón de logout - Solo crear si hide_logout es False
        if not self.hide_logout:
            logout_button = QPushButton("Cerrar Sesión")
            logout_button.clicked.connect(self.logout)
            right_layout.addWidget(logout_button)

        header_layout.addLayout(right_layout)

        return header_widget
