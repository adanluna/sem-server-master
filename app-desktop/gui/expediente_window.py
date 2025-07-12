from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QLineEdit, QPushButton, QSpacerItem,
                               QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from gui.base_window import BaseWindowWithHeader
from services.api_client import ApiClient
import logging


class ExpedienteWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre="", config_service=None):
        super().__init__(
            medico_nombre=medico_nombre,
            config_service=config_service,
            window_title="SEMEFO - Expediente"
        )
        self.api_client = ApiClient(config_service)
        self.init_ui()

    def init_ui(self):
        # Layout principal para el contenido
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Espaciador superior
        layout.addItem(QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Título
        title_label = QLabel("Nuevo Expediente")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Formulario
        form_widget = QWidget()
        form_widget.setMaximumWidth(500)
        form_layout = QFormLayout(form_widget)

        # Campo número de expediente
        expediente_label = QLabel("Número de Expediente:")
        expediente_label.setProperty("class", "section-title")
        self.input_expediente = QLineEdit()
        self.input_expediente.setPlaceholderText("Ej: EXP-2024-001")
        form_layout.addRow(expediente_label, self.input_expediente)

        # Campo nombre de sesión
        sesion_label = QLabel("Nombre de la Sesión:")
        sesion_label.setProperty("class", "section-title")
        self.input_sesion = QLineEdit()
        self.input_sesion.setPlaceholderText("Ej: Autopsia inicial")
        self.input_sesion.returnPressed.connect(self.go_to_next)
        form_layout.addRow(sesion_label, self.input_sesion)

        # Centrar formulario
        form_container_layout = QHBoxLayout()
        form_container_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        form_container_layout.addWidget(form_widget)
        form_container_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(form_container_layout)

        # Botón continuar
        button_layout = QHBoxLayout()
        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.button_continuar = QPushButton("Continuar")
        self.button_continuar.setProperty("class", "action-button")
        self.button_continuar.clicked.connect(self.go_to_next)
        button_layout.addWidget(self.button_continuar)

        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_layout)

        # Espaciador inferior
        layout.addItem(QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def go_to_next(self):
        expediente = self.input_expediente.text()
        sesion = self.input_sesion.text()
        if not expediente or not sesion:
            QMessageBox.warning(
                self, "Campos requeridos", "Por favor ingrese número de expediente y nombre de sesión.")
            return

        try:
            # Buscar o crear expediente
            id_expediente = self.api_client.buscar_o_crear_expediente(
                expediente)

            # Crear sesión con username
            id_sesion = self.api_client.crear_sesion_sin_validacion(
                numero_expediente=expediente,
                descripcion=sesion,
                usuario_ldap=self.medico_nombre
            )

            logging.info(
                f"Expediente {expediente} (id {id_expediente}), sesión {sesion} (id {id_sesion}) creado.")

            # Continuar a grabación
            from gui.grabar_window import GrabarWindow
            self.grabar_window = GrabarWindow(
                self.medico_nombre,
                expediente,
                sesion,
                self.config_service,
                id_sesion=id_sesion
            )
            self.grabar_window.show()
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error al crear sesión", str(e))
            logging.error(f"Error al crear sesión: {e}")
