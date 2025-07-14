from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QLineEdit, QPushButton, QSpacerItem,
                               QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from gui.base_window import BaseWindowWithHeader
from services.api_client import ApiClient
import logging


class ExpedienteWindow(BaseWindowWithHeader):
    # ✅ Agregar username_ldap
    def __init__(self, medico_nombre="", config_service=None, username_ldap=None):
        super().__init__(
            medico_nombre=medico_nombre,
            config_service=config_service,
            window_title="SEMEFO - Expediente"
        )
        self.api_client = ApiClient(config_service)
        self.username_ldap = username_ldap  # ✅ Guardar el username LDAP
        self.init_ui()

    def init_ui(self):
        # ✅ SOLO AGREGAR: Limpiar layout existente
        if self.content_widget.layout() is not None:
            QWidget().setLayout(self.content_widget.layout())

        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Espaciador superior
        layout.addItem(QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Título
        title_label = QLabel("Nueva Sesión")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Formulario
        form_widget = QWidget()
        form_widget.setMaximumWidth(700)
        form_layout = QFormLayout(form_widget)

        # Campo número de expediente
        expediente_label = QLabel("Número de Expediente:")
        expediente_label.setProperty("class", "section-title")
        self.input_expediente = QLineEdit()
        self.input_expediente.setPlaceholderText("Ej: EXP-2024-001")
        self.input_expediente.setMinimumWidth(450)
        form_layout.addRow(expediente_label, self.input_expediente)

        # Campo nombre de sesión
        sesion_label = QLabel("Nombre de la Sesión:")
        sesion_label.setProperty("class", "section-title")
        self.input_sesion = QLineEdit()
        self.input_sesion.setPlaceholderText("Ej: Autopsia inicial")
        self.input_sesion.setMinimumWidth(450)
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
        """Navegar a la siguiente pantalla - grabación"""
        try:
            numero_expediente = self.input_expediente.text().strip()
            nombre_sesion = self.input_sesion.text().strip()

            if not numero_expediente or not nombre_sesion:
                QMessageBox.warning(
                    self, "Campos requeridos",
                    "Por favor complete todos los campos."
                )
                return

            # ✅ Usar username_ldap y medico_nombre correctamente
            usuario_ldap = self.username_ldap
            user_nombre = self.medico_nombre  # ✅ Nombre completo del médico

            print(f"🔍 DEBUG: Creando sesión con usuario_ldap: {usuario_ldap}")
            print(f"🔍 DEBUG: user_nombre: {user_nombre}")

            # Crear sesión con ambos parámetros
            id_sesion = self.api_client.crear_sesion(
                numero_expediente=numero_expediente,
                descripcion=nombre_sesion,
                usuario_ldap=usuario_ldap,  # ✅ Username (ej: "forense1")
                # ✅ Nombre completo (ej: "Forense 1 F1. Martinez")
                user_nombre=user_nombre
            )

            if id_sesion:
                # ✅ Continuar a la pantalla de grabación
                from gui.grabar_window import GrabarWindow

                self.grabar_window = GrabarWindow(
                    medico_nombre=self.medico_nombre,
                    numero_expediente=numero_expediente,
                    nombre_sesion=nombre_sesion,
                    id_sesion=id_sesion,
                    config_service=self.config_service,
                    username_ldap=usuario_ldap
                )
                self.grabar_window.show()
                self.close()

        except Exception as e:
            logging.error(f"Error al crear sesión: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Error al crear sesión: {str(e)}"
            )
