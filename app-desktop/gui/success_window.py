import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSpacerItem, QSizePolicy, QProgressBar)
from PySide6.QtCore import Qt, QTimer
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
        self.process_files()

    def init_ui(self):
        # Layout principal para el contenido
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Espaciador superior
        layout.addItem(QSpacerItem(
            20, 50, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Título de éxito
        success_title = QLabel("✅ Sesión Completada")
        success_title.setProperty("class", "success-title")
        success_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(success_title)

        # Detalles
        details_label = QLabel(
            f"Los archivos de la sesión '{self.nombre_sesion}'\ndel expediente {self.numero_expediente}\nhan sido enviados a procesamiento.")
        details_label.setProperty("class", "success-details")
        details_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(details_label)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Estado del procesamiento
        self.status_label = QLabel("Iniciando procesamiento...")
        self.status_label.setProperty("class", "status-text")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Botones
        button_layout = QHBoxLayout()
        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.button_new_session = QPushButton("Nueva Sesión")
        self.button_new_session.setProperty("class", "action-button")
        self.button_new_session.clicked.connect(self.new_session)
        self.button_new_session.setEnabled(False)
        button_layout.addWidget(self.button_new_session)

        self.button_exit = QPushButton("Salir")
        self.button_exit.setProperty("class", "cancel-button")
        self.button_exit.clicked.connect(self.exit_app)
        button_layout.addWidget(self.button_exit)

        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_layout)

        # Espaciador inferior
        layout.addItem(QSpacerItem(
            20, 50, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def process_files(self):
        """Simular el procesamiento de archivos"""
        try:
            # Simular progreso
            self.progress_timer = QTimer()
            self.progress_timer.timeout.connect(self.update_progress)
            self.progress_value = 0
            self.progress_timer.start(100)  # Actualizar cada 100ms

            # Procesar audio
            if self.api_client.procesar_audio(self.numero_expediente, self.id_sesion):
                logging.info("Audio enviado a procesamiento")

            # Procesar video
            if self.api_client.procesar_video(self.numero_expediente, self.id_sesion):
                logging.info("Video enviado a procesamiento")

        except Exception as e:
            logging.error(f"Error procesando archivos: {e}")
            self.status_label.setText("❌ Error en el procesamiento")

    def update_progress(self):
        """Actualizar la barra de progreso"""
        self.progress_value += 2
        self.progress_bar.setValue(self.progress_value)

        if self.progress_value >= 100:
            self.progress_timer.stop()
            self.status_label.setText("✅ Procesamiento completado")
            self.button_new_session.setEnabled(True)

    def new_session(self):
        """Crear nueva sesión"""
        try:
            from gui.expediente_window import ExpedienteWindow
            self.expediente_window = ExpedienteWindow(
                self.medico_nombre, self.config_service)
            self.expediente_window.show()
            self.close()
        except Exception as e:
            logging.error(f"Error abriendo nueva sesión: {e}")

    def exit_app(self):
        """Salir de la aplicación"""
        self.close()
