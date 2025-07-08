from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from services.utils import load_stylesheet
from gui.components.header_widget import HeaderWidget

# Constantes para consistencia
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 700
HEADER_HEIGHT = 100


class BaseWindow(QWidget):
    """Clase base para todas las ventanas de la aplicación"""

    def __init__(self, window_title="SEMEFO"):
        super().__init__()
        self.setWindowTitle(window_title)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        load_stylesheet(self)

    def setup_layout_with_header(self, header_widget, content_widget):
        """Configurar layout estándar con header fijo y contenido"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # Sin márgenes
        main_layout.setSpacing(0)  # Sin espaciado
        main_layout.addWidget(header_widget)
        main_layout.addWidget(content_widget)
        self.setLayout(main_layout)

    def setup_layout_without_header(self, content_widget):
        """Configurar layout sin header (para login y config)"""
        main_layout = QVBoxLayout()
        main_layout.addWidget(content_widget)
        self.setLayout(main_layout)


class BaseWindowWithHeader(BaseWindow):
    """Clase base para ventanas que usan HeaderWidget"""

    def __init__(self, medico_nombre, numero_expediente="", nombre_sesion="", config_service=None, window_title="SEMEFO"):
        super().__init__(window_title)
        self.medico_nombre = medico_nombre
        self.config_service = config_service
        self.numero_expediente = numero_expediente
        self.nombre_sesion = nombre_sesion

        # Crear header fijo
        self.header = HeaderWidget(
            self.medico_nombre,
            self.numero_expediente,
            self.nombre_sesion,
            self.config_service
        )

    def setup_content(self, content_widget):
        """Configurar contenido con header ya creado"""
        self.setup_layout_with_header(self.header, content_widget)

    def update_expediente_info(self, numero_expediente, nombre_sesion):
        """Actualizar información del expediente en el header"""
        self.numero_expediente = numero_expediente
        self.nombre_sesion = nombre_sesion
        if hasattr(self.header, 'update_expediente_info'):
            self.header.update_expediente_info(
                numero_expediente, nombre_sesion)
