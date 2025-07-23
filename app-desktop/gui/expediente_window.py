from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QLineEdit, QPushButton, QSpacerItem,
                               QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from gui.base_window import BaseWindowWithHeader
from services.api_client import ApiClient
import logging
import os
import shutil


class ExpedienteWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre="", config_service=None, username_ldap=None):
        super().__init__(
            medico_nombre=medico_nombre,
            config_service=config_service,
            window_title="SEMEFO - Expediente"
        )
        self.api_client = ApiClient(config_service)
        self.username_ldap = username_ldap
        self.init_ui()

    def init_ui(self):
        if self.content_widget.layout() is not None:
            QWidget().setLayout(self.content_widget.layout())

        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.addItem(QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        title_label = QLabel("Nueva Sesión")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        form_widget = QWidget()
        form_widget.setMaximumWidth(700)
        form_layout = QFormLayout(form_widget)

        expediente_label = QLabel("Número de Expediente:")
        expediente_label.setProperty("class", "section-title")
        self.input_expediente = QLineEdit()
        self.input_expediente.setPlaceholderText("Ej: EXP-2024-001")
        self.input_expediente.setMinimumWidth(450)
        form_layout.addRow(expediente_label, self.input_expediente)

        sesion_label = QLabel("Nombre de la Sesión:")
        sesion_label.setProperty("class", "section-title")
        self.input_sesion = QLineEdit()
        self.input_sesion.setPlaceholderText("Ej: Autopsia inicial")
        self.input_sesion.setMinimumWidth(450)
        self.input_sesion.returnPressed.connect(self.go_to_next)
        form_layout.addRow(sesion_label, self.input_sesion)

        form_container_layout = QHBoxLayout()
        form_container_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        form_container_layout.addWidget(form_widget)
        form_container_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(form_container_layout)

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
        layout.addItem(QSpacerItem(
            20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def go_to_next(self):
        try:
            numero_expediente = self.input_expediente.text().strip()
            nombre_sesion = self.input_sesion.text().strip()

            if not numero_expediente or not nombre_sesion:
                QMessageBox.warning(self, "Campos requeridos",
                                    "Por favor complete todos los campos.")
                return

            usuario_ldap = self.username_ldap
            user_nombre = self.medico_nombre

            id_sesion = self.api_client.crear_sesion(
                numero_expediente=numero_expediente,
                descripcion=nombre_sesion,
                usuario_ldap=usuario_ldap,
                user_nombre=user_nombre
            )

            if id_sesion:
                # Copia a archivos_grabados (respaldo crudo)
                origen_audio = "storage_test/audios"
                origen_video = "storage_test/videos"
                origen_video2 = "storage_test/videos2"

                destino_audio = f"storage/archivos_grabados/{numero_expediente}/{id_sesion}/audios"
                destino_video = f"storage/archivos_grabados/{numero_expediente}/{id_sesion}/videos"
                destino_video2 = f"storage/archivos_grabados/{numero_expediente}/{id_sesion}/videos2"

                os.makedirs(destino_audio, exist_ok=True)
                os.makedirs(destino_video, exist_ok=True)

                for f in os.listdir(origen_audio):
                    shutil.copy2(os.path.join(origen_audio, f), destino_audio)
                for f in os.listdir(origen_video):
                    shutil.copy2(os.path.join(origen_video, f), destino_video)

                # ✅ Copiar carpeta videos2 si existe
                if os.path.exists(origen_video2):
                    os.makedirs(destino_video2, exist_ok=True)
                    for f in os.listdir(origen_video2):
                        shutil.copy2(os.path.join(
                            origen_video2, f), destino_video2)

                # ✅ Copia a archivos (para que el worker tenga audios/videos a unir)
                destino_audio_final = f"storage/archivos/{numero_expediente}/{id_sesion}/audios"
                destino_video_final = f"storage/archivos/{numero_expediente}/{id_sesion}/videos"

                os.makedirs(destino_audio_final, exist_ok=True)
                os.makedirs(destino_video_final, exist_ok=True)

                for f in os.listdir(origen_audio):
                    shutil.copy2(os.path.join(origen_audio, f),
                                 destino_audio_final)
                for f in os.listdir(origen_video):
                    shutil.copy2(os.path.join(origen_video, f),
                                 destino_video_final)

                # Mostrar siguiente ventana
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
                self, "Error", f"Error al crear sesión: {str(e)}")
