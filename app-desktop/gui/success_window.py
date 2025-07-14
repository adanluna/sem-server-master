import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt
from gui.base_window import BaseWindowWithHeader
from services.api_client import ApiClient
import logging


class SuccessWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre="", numero_expediente="", nombre_sesion="", config_service=None, id_sesion=None, username_ldap=None):  # ✅ Agregar username_ldap
        super().__init__(
            medico_nombre=medico_nombre,
            numero_expediente=numero_expediente,
            nombre_sesion=nombre_sesion,
            config_service=config_service,
            window_title="SEMEFO - Procesamiento"
        )
        self.api_client = ApiClient(config_service)
        self.id_sesion = id_sesion
        self.username_ldap = username_ldap  # ✅ Guardar username_ldap
        self.init_ui()

    def init_ui(self):
        # Layout principal para el contenido
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Espaciador superior
        layout.addItem(QSpacerItem(
            20, 50, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Título de éxito
        success_title = QLabel("✅ Grabación terminada")
        success_title.setProperty("class", "success-title")
        success_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(success_title)

        # Detalles de la grabación
        details_label = QLabel(
            f"La grabación de la sesión '<b>{self.nombre_sesion}</b>'\n"
            f"del expediente <b>{self.numero_expediente}</b>\n"
            f"ha sido completada exitosamente."
        )
        details_label.setProperty("class", "success-details")
        details_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(details_label)

        # ✅ AGREGAR: Mensaje de procesamiento
        process_info = QLabel(
            "Los archivos de audio y video han sido enviados\n"
            "a procesamiento automático."
        )
        process_info.setProperty("class", "status-text")
        process_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(process_info)

        # ✅ CAMBIAR: Solo botón "Terminar sesión"
        button_layout = QHBoxLayout()
        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.button_finish_session = QPushButton("Terminar Sesión")
        self.button_finish_session.setProperty("class", "action-button")
        self.button_finish_session.clicked.connect(self.finish_session)
        button_layout.addWidget(self.button_finish_session)

        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_layout)

        # Espaciador inferior
        layout.addItem(QSpacerItem(
            20, 50, QSizePolicy.Minimum, QSizePolicy.Expanding))

    # ✅ CAMBIAR: Método para terminar sesión y volver al login
    def finish_session(self):
        """Terminar sesión y volver al login"""
        try:
            from gui.login_window import LoginWindow

            self.login_window = LoginWindow(self.config_service)
            self.login_window.show()
            self.close()

        except Exception as e:
            logging.error(f"Error volviendo al login: {e}")
