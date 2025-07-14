import os
import shutil
import requests
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSpacerItem, QSizePolicy, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from gui.base_window import BaseWindowWithHeader
from services.api_client import ApiClient
from services.audio_recorder import AudioRecorder
import logging


class GrabarWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre="", numero_expediente="", nombre_sesion="", config_service=None, id_sesion=None, username_ldap=None):
        super().__init__(
            medico_nombre=medico_nombre,
            numero_expediente=numero_expediente,
            nombre_sesion=nombre_sesion,
            config_service=config_service,
            window_title="SEMEFO - Grabación",
            hide_logout=True  # ✅ Ocultar botón de cerrar sesión
        )
        self.api_client = ApiClient(config_service)
        self.id_sesion = id_sesion
        self.username_ldap = username_ldap
        self.audio_recorder = AudioRecorder()

        # Estados de grabación
        self.is_recording = False
        self.is_paused = False

        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_timer)
        self.recording_time = 0
        self.init_ui()

    def init_ui(self):
        # Layout principal para el contenido
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(40)  # ✅ Más espacio entre elementos

        # Espaciador superior
        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Título
        title_label = QLabel("Sesión de Grabación")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Estado de grabación
        self.status_label = QLabel("Listo para iniciar grabación")
        self.status_label.setProperty("class", "recording-status")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Timer
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setProperty("class", "timer-label")
        self.timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.timer_label)

        # ✅ Botones de control - GRANDES Y REDONDOS
        button_layout = QVBoxLayout()  # ✅ Cambiar a vertical para botones más grandes
        button_layout.setSpacing(30)  # ✅ Más espacio entre botones

        # ✅ Botón INICIAR (solo visible al inicio)
        self.button_start = QPushButton("🔴\nIniciar\nGrabación")
        self.button_start.setProperty(
            "class", "large-round-button start-button")
        self.button_start.clicked.connect(self.start_recording)
        self.button_start.setMinimumSize(200, 150)  # ✅ Tamaño mínimo grande
        self.button_start.setMaximumSize(300, 180)  # ✅ Tamaño máximo
        button_layout.addWidget(self.button_start, alignment=Qt.AlignCenter)

        # ✅ Layout horizontal para botones de control (pausar/continuar + finalizar)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(40)  # ✅ Espacio entre botones

        # ✅ Botón PAUSAR (solo visible cuando está grabando)
        self.button_pause = QPushButton("⏸\nPausar")
        self.button_pause.setProperty(
            "class", "large-round-button pause-button")
        self.button_pause.clicked.connect(self.pause_recording)
        self.button_pause.setMinimumSize(180, 130)
        self.button_pause.setMaximumSize(220, 150)
        self.button_pause.setVisible(False)
        control_layout.addWidget(self.button_pause)

        # ✅ Botón CONTINUAR (solo visible cuando está pausado)
        self.button_continue = QPushButton("▶️\nContinuar")
        self.button_continue.setProperty(
            "class", "large-round-button continue-button")
        self.button_continue.clicked.connect(self.continue_recording)
        self.button_continue.setMinimumSize(180, 130)
        self.button_continue.setMaximumSize(220, 150)
        self.button_continue.setVisible(False)
        control_layout.addWidget(self.button_continue)

        # ✅ Botón FINALIZAR (visible cuando está grabando o pausado)
        self.button_finish = QPushButton("✅\nFinalizar")
        self.button_finish.setProperty(
            "class", "large-round-button finish-button")
        self.button_finish.clicked.connect(self.finish_session)
        self.button_finish.setMinimumSize(180, 130)
        self.button_finish.setMaximumSize(220, 150)
        self.button_finish.setVisible(False)
        control_layout.addWidget(self.button_finish)

        button_layout.addLayout(control_layout)
        layout.addLayout(button_layout)

        # Espaciador inferior
        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def start_recording(self):
        """Iniciar grabación"""
        try:
            print(f"🔍 DEBUG: Iniciando grabación sesión {self.id_sesion}")

            # Iniciar grabación de audio
            audio_filename = f"sesion_{self.id_sesion}_audio.wav"
            if self.audio_recorder.start_recording(audio_filename):
                logging.info("Grabación de audio iniciada")
            else:
                QMessageBox.warning(
                    self, "Error", "No se pudo iniciar la grabación de audio")
                return

            # SIMULADO: Enviar comando a cámara para iniciar grabación
            print("📹 SIMULADO: Enviando comando a cámara para iniciar grabación")

            # Actualizar estado
            self.is_recording = True
            self.is_paused = False

            # Actualizar UI - Mostrar botones de PAUSAR y FINALIZAR
            self.button_start.setVisible(False)
            self.button_pause.setVisible(True)
            self.button_continue.setVisible(False)
            self.button_finish.setVisible(True)

            self.status_label.setText("🔴 Grabando...")

            # Iniciar timer
            self.recording_time = 0
            self.recording_timer.start(1000)  # Actualizar cada segundo

            logging.info(f"Grabación iniciada: {self.id_sesion}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error iniciando grabación: {str(e)}")
            logging.error(f"Error iniciando grabación: {e}")

    def pause_recording(self):
        """Pausar grabación"""
        try:
            print(f"🔍 DEBUG: Pausando grabación sesión {self.id_sesion}")

            # Pausar timer
            self.recording_timer.stop()

            # SIMULADO: Pausar grabación (en la implementación real sería pause)
            print("📹 SIMULADO: Pausando grabación de cámara")
            print("🎤 SIMULADO: Pausando grabación de audio")

            # Actualizar estado
            self.is_paused = True

            # Actualizar UI - Mostrar botones de CONTINUAR y FINALIZAR
            self.button_start.setVisible(False)
            self.button_pause.setVisible(False)
            self.button_continue.setVisible(True)
            self.button_finish.setVisible(True)

            self.status_label.setText("⏸ Grabación pausada")

            logging.info(f"Grabación pausada: {self.id_sesion}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error pausando grabación: {str(e)}")
            logging.error(f"Error pausando grabación: {e}")

    def continue_recording(self):
        """Continuar grabación después de pausa"""
        try:
            print(f"🔍 DEBUG: Continuando grabación sesión {self.id_sesion}")

            # SIMULADO: Continuar grabación
            print("📹 SIMULADO: Continuando grabación de cámara")
            print("🎤 SIMULADO: Continuando grabación de audio")

            # Actualizar estado
            self.is_paused = False

            # Actualizar UI - Mostrar botones de PAUSAR y FINALIZAR
            self.button_start.setVisible(False)
            self.button_pause.setVisible(True)
            self.button_continue.setVisible(False)
            self.button_finish.setVisible(True)

            self.status_label.setText("🔴 Grabando...")

            # Continuar timer
            self.recording_timer.start(1000)

            logging.info(f"Grabación continuada: {self.id_sesion}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error continuando grabación: {str(e)}")
            logging.error(f"Error continuando grabación: {e}")

    def finish_session(self):
        """Finalizar sesión y procesar datos"""
        try:
            # ✅ Crear QMessageBox personalizado para mejor control
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Finalizar Sesión")
            msg_box.setText("¿Está seguro de que desea finalizar la sesión?")
            msg_box.setIcon(QMessageBox.Question)

            # ✅ Agregar botones personalizados
            yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
            no_button = msg_box.addButton("No", QMessageBox.NoRole)

            # ✅ Establecer botón por defecto
            msg_box.setDefaultButton(no_button)

            # ✅ Mostrar el diálogo
            msg_box.exec()

            # ✅ Verificar qué botón se presionó
            if msg_box.clickedButton() != yes_button:
                return

            print(f"🔍 DEBUG: Finalizando sesión {self.id_sesion}")

            # Detener timer si está corriendo
            self.recording_timer.stop()

            # Detener grabación
            self.audio_recorder.stop_recording()
            logging.info("Grabación de audio finalizada")

            # SIMULADO: Detener grabación de cámara
            print("📹 SIMULADO: Finalizando grabación de cámara")

            # Actualizar estado
            self.is_recording = False
            self.is_paused = False

            # ✅ Llamar al API para finalizar sesión en la base de datos
            # self.api_client.finalizar_sesion(self.id_sesion)

            # ✅ Ir a pantalla de éxito con procesamiento
            from gui.success_window import SuccessWindow
            self.success_window = SuccessWindow(
                medico_nombre=self.medico_nombre,
                numero_expediente=self.numero_expediente,
                nombre_sesion=self.nombre_sesion,
                config_service=self.config_service,
                id_sesion=self.id_sesion,
                username_ldap=self.username_ldap
            )
            self.success_window.show()
            self.close()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error finalizando sesión: {str(e)}")
            logging.error(f"Error finalizando sesión: {e}")

    def update_timer(self):
        """Actualizar el timer de la sesión"""
        self.recording_time += 1
        hours = self.recording_time // 3600
        minutes = (self.recording_time % 3600) // 60
        seconds = self.recording_time % 60
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
