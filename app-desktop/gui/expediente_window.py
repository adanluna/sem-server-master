from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget
from PySide6.QtCore import Qt
import logging
from gui.base_window import BaseWindowWithHeader
from gui.grabar_window import GrabarWindow

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ExpedienteWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre="", config_service=None):
        super().__init__(
            medico_nombre=medico_nombre,
            config_service=config_service,
            window_title="SEMEFO - Expediente"
        )
        self.init_ui()

    def init_ui(self):
        # Crear el contenido (stack widget)
        self.stacked_widget = QStackedWidget()
        self.page_expediente = self.create_expediente_page()
        self.stacked_widget.addWidget(self.page_expediente)

        # Configurar layout usando la clase base
        self.setup_content(self.stacked_widget)

    def create_expediente_page(self):
        page = QWidget()
        page_layout = QVBoxLayout()
        # Márgenes para el contenido
        page_layout.setContentsMargins(20, 20, 20, 20)

        # Formulario centrado
        form_container = QWidget()
        form_container.setFixedSize(400, 300)
        form_layout = QVBoxLayout(form_container)
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(20)

        self.input_expediente = QLineEdit()
        self.input_expediente.setPlaceholderText("Número de expediente")
        self.input_expediente.setFixedHeight(40)

        self.input_sesion = QLineEdit()
        self.input_sesion.setPlaceholderText("Nombre de la sesión")
        self.input_sesion.setFixedHeight(40)

        continuar_btn = QPushButton("Continuar")
        continuar_btn.setProperty("class", "action-button")
        continuar_btn.setFixedSize(120, 40)
        continuar_btn.clicked.connect(self.go_to_next)

        form_layout.addWidget(QLabel("Número de expediente"))
        form_layout.addWidget(self.input_expediente)
        form_layout.addWidget(QLabel("Nombre de la sesión"))
        form_layout.addWidget(self.input_sesion)
        form_layout.addWidget(continuar_btn)

        # Centrar el formulario
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(form_container)
        center_layout.addStretch()

        page_layout.addStretch()
        page_layout.addLayout(center_layout)
        page_layout.addStretch()
        page.setLayout(page_layout)
        return page

    def go_to_next(self):
        expediente = self.input_expediente.text()
        sesion = self.input_sesion.text()
        if not expediente or not sesion:
            QMessageBox.warning(
                self, "Campos requeridos", "Por favor ingrese número de expediente y nombre de sesión.")
            return

        self.numero_expediente = expediente
        self.nombre_sesion = sesion

        logging.info(
            f"Expediente {expediente} y sesión {sesion} capturados. Avanzando a grabar.")

        self.grabar_window = GrabarWindow(
            self.medico_nombre, self.numero_expediente, self.nombre_sesion, self.config_service)
        self.grabar_window.show()
        self.close()
