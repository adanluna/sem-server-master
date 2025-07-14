from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import logging


class BaseWindow(QWidget):
    def __init__(self, config_service=None, window_title="SEMEFO"):
        super().__init__()
        self.config_service = config_service
        self.setWindowTitle(window_title)
        # ✅ AGREGAR: Tamaño estándar para todas las ventanas
        self.resize(1024, 768)
        self.center_window()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.content_widget = QWidget()
        main_layout.addWidget(self.content_widget)

    # ✅ AGREGAR: Método para centrar ventana
    def center_window(self):
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def logout(self):
        try:
            from gui.login_window import LoginWindow
            self.login_window = LoginWindow(self.config_service)
            self.login_window.show()
            self.close()
        except Exception as e:
            logging.error(f"Error en logout: {e}")


class BaseWindowWithHeader(BaseWindow):
    def __init__(self, medico_nombre="", numero_expediente="", nombre_sesion="", config_service=None, window_title="SEMEFO", hide_logout=False):
        super().__init__(config_service, window_title)
        self.medico_nombre = medico_nombre
        self.numero_expediente = numero_expediente
        self.nombre_sesion = nombre_sesion
        self.hide_logout = hide_logout

        self.init_ui()

        main_layout = self.layout()
        main_layout.removeWidget(self.content_widget)

        header_widget = self.create_header()
        main_layout.addWidget(header_widget)
        main_layout.addWidget(self.content_widget)

    def create_header(self):
        header_widget = QWidget()
        header_widget.setFixedHeight(100)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(20)

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
        logo_label.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(logo_label)
        header_layout.addLayout(logo_layout)

        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setSpacing(5)

        if self.numero_expediente:
            expediente_label = QLabel(
                f"Expediente: <b>{self.numero_expediente}</b>")
            expediente_label.setAlignment(Qt.AlignCenter)
            center_layout.addWidget(expediente_label)

        if self.nombre_sesion:
            sesion_label = QLabel(f"Sesión: <b>{self.nombre_sesion}</b>")
            sesion_label.setAlignment(Qt.AlignCenter)
            center_layout.addWidget(sesion_label)

        if not self.numero_expediente and not self.nombre_sesion:
            center_layout.addItem(QSpacerItem(
                20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        header_layout.addLayout(center_layout)

        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setSpacing(8)

        if self.medico_nombre:
            user_label = QLabel(self.medico_nombre)
            user_label.setAlignment(Qt.AlignCenter)
            # ✅ AGREGAR: Texto en negritas
            user_label.setStyleSheet("font-weight: bold;")
            right_layout.addWidget(user_label)

        if not self.hide_logout:
            logout_button = QPushButton("Cerrar Sesión")
            logout_button.setObjectName("logout-button")
            logout_button.clicked.connect(self.logout)
            right_layout.addWidget(logout_button)

        header_layout.addLayout(right_layout)

        return header_widget
