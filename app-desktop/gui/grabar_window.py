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
    def __init__(self, medico_nombre="", numero_expediente="", nombre_sesion="", id_sesion=None, config_service=None, username_ldap=""):
        super().__init__(
            medico_nombre=medico_nombre,
            numero_expediente=numero_expediente,
            nombre_sesion=nombre_sesion,
            config_service=config_service,
            window_title="SEMEFO - Grabación"
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
        # ✅ AGREGAR: Verificar si ya se inicializó la UI
        if hasattr(self, 'button_start'):
            return

        # ✅ AGREGAR: Variables para tamaños de botones
        BUTTON_WIDTH = 200
        BUTTON_HEIGHT = 150
        BUTTON_SPACING = 20

        # ✅ AGREGAR: Limpiar layout existente si existe
        if self.content_widget.layout() is not None:
            QWidget().setLayout(self.content_widget.layout())

        # Layout principal para el contenido
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(40)

        # Espaciador superior
        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Estado de grabación - ✅ FIJAR altura y tamaño
        self.status_label = QLabel("Listo para iniciar grabación")
        self.status_label.setProperty("class", "recording-status")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(60)  # ✅ Altura fija
        self.status_label.setMinimumWidth(400)  # ✅ Ancho mínimo
        layout.addWidget(self.status_label)

        # Timer - ✅ FIJAR altura y tamaño
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setProperty("class", "timer-label")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFixedHeight(50)  # ✅ Altura fija
        self.timer_label.setMinimumWidth(200)  # ✅ Ancho mínimo
        layout.addWidget(self.timer_label)

        # ✅ AGREGAR: Contenedor de altura fija para todos los botones
        button_container = QWidget()
        # ✅ Altura fija para evitar movimiento
        button_container.setFixedHeight(200)
        button_container_layout = QVBoxLayout(button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(20)
        button_container_layout.setAlignment(Qt.AlignCenter)

        # ✅ Botón INICIAR - Usando variables
        self.button_start = QPushButton("🔴\nIniciar\nGrabación")
        self.button_start.setProperty("class", "start-button")
        self.button_start.clicked.connect(self.start_recording)
        self.button_start.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        button_container_layout.addWidget(
            self.button_start, alignment=Qt.AlignCenter)

        # ✅ Botón PAUSAR - Usando variables
        self.button_pause = QPushButton("⏸\nPausar")
        self.button_pause.setProperty("class", "pause-button")
        self.button_pause.clicked.connect(self.pause_recording)
        self.button_pause.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.button_pause.setVisible(False)

        # ✅ Botón CONTINUAR - Usando variables
        self.button_continue = QPushButton("▶️\nContinuar")
        self.button_continue.setProperty("class", "continue-button")
        self.button_continue.clicked.connect(self.continue_recording)
        self.button_continue.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.button_continue.setVisible(False)

        # ✅ Botón FINALIZAR - Usando variables
        self.button_finish = QPushButton("✅\nFinalizar")
        self.button_finish.setProperty("class", "finish-button")
        self.button_finish.clicked.connect(self.finish_session)
        self.button_finish.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.button_finish.setVisible(False)

        # ✅ Layout horizontal para los botones de grabación
        horizontal_buttons_layout = QHBoxLayout()
        horizontal_buttons_layout.setSpacing(BUTTON_SPACING)
        horizontal_buttons_layout.setAlignment(Qt.AlignCenter)
        horizontal_buttons_layout.addWidget(self.button_pause)
        horizontal_buttons_layout.addWidget(self.button_continue)
        horizontal_buttons_layout.addWidget(self.button_finish)

        # ✅ Agregar el layout horizontal al contenedor
        button_container_layout.addLayout(horizontal_buttons_layout)

        # ✅ Agregar el contenedor de altura fija al layout principal
        layout.addWidget(button_container, alignment=Qt.AlignCenter)

        # Espaciador inferior
        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # ✅ AGREGAR: Asegurar que los botones estén embebidos en la ventana principal
        self.button_pause.setParent(button_container)
        self.button_continue.setParent(button_container)
        self.button_finish.setParent(button_container)
        self.button_start.setParent(button_container)

    def start_recording(self):
        """Iniciar grabación"""
        try:
            # Iniciar grabación de audio
            audio_filename = f"sesion_{self.id_sesion}_audio.wav"
            if self.audio_recorder.start_recording(audio_filename):
                logging.info("Grabación de audio iniciada")
            else:
                QMessageBox.warning(
                    self, "Error", "No se pudo iniciar la grabación de audio")
                return

            # SIMULADO: Enviar comando a cámara para iniciar grabación

            # Actualizar estado
            self.is_recording = True
            self.is_paused = False

            # Actualizar UI - Mostrar botones de PAUSAR y FINALIZAR
            self.button_start.setVisible(False)
            self.button_pause.setVisible(True)
            self.button_continue.setVisible(False)
            self.button_finish.setVisible(True)

            self.status_label.setText("🔴 Grabando...")  # ✅ Texto consistente

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
            # Pausar timer
            self.recording_timer.stop()

            # SIMULADO: Pausar grabación (en la implementación real sería pause)
            # Actualizar estado
            self.is_paused = True

            # Actualizar UI - Mostrar botones de CONTINUAR y FINALIZAR
            self.button_start.setVisible(False)
            self.button_pause.setVisible(False)
            self.button_continue.setVisible(True)
            self.button_finish.setVisible(True)  # ✅ Siempre visible

            self.status_label.setText(
                "⏸ Grabación pausada")  # ✅ Texto consistente

            logging.info(f"Grabación pausada: {self.id_sesion}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error pausando grabación: {str(e)}")
            logging.error(f"Error pausando grabación: {e}")

    def continue_recording(self):
        """Continuar grabación"""
        try:
            # SIMULADO: Continuar grabación

            # Actualizar estado
            self.is_paused = False

            # Actualizar UI - Mostrar botones de PAUSAR y FINALIZAR
            self.button_start.setVisible(False)
            self.button_pause.setVisible(True)
            self.button_continue.setVisible(False)
            self.button_finish.setVisible(True)  # ✅ Siempre visible

            self.status_label.setText("🔴 Grabando...")  # ✅ Texto consistente

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
            # ✅ AGREGAR: Pausar grabación temporalmente
            was_recording = self.is_recording and not self.is_paused
            if was_recording:
                self.recording_timer.stop()
                self.audio_recorder.pause_recording() if hasattr(
                    self.audio_recorder, 'pause_recording') else None

            # ✅ Crear QMessageBox personalizado para mejor control
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Finalizar Sesión")
            msg_box.setText("¿Está seguro de que desea finalizar la sesión?")
            msg_box.setIcon(QMessageBox.Question)

            # ✅ CAMBIAR: Usar la nueva clase gray-button
            no_button = msg_box.addButton("No", QMessageBox.NoRole)
            yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)

            # ✅ USAR: Clase del styles.qss
            no_button.setProperty("class", "gray-button")
            yes_button.setProperty("class", "action-button")

            # ✅ FORZAR: Aplicar el stylesheet
            no_button.style().unpolish(no_button)
            no_button.style().polish(no_button)
            yes_button.style().unpolish(yes_button)
            yes_button.style().polish(yes_button)

            # ✅ Establecer botón por defecto
            msg_box.setDefaultButton(no_button)

            # ✅ Mostrar el diálogo
            result = msg_box.exec()

            # ✅ AGREGAR: Si dijo "No", reanudar grabación
            if msg_box.clickedButton() == no_button:
                if was_recording:
                    self.audio_recorder.resume_recording() if hasattr(
                        self.audio_recorder, 'resume_recording') else None
                    self.recording_timer.start(1000)
                return

            # ✅ Solo continuar si presionó "Sí"
            if msg_box.clickedButton() != yes_button:
                return

            # Detener timer si está corriendo
            self.recording_timer.stop()

            # Detener grabación
            self.audio_recorder.stop_recording()
            logging.info("Grabación de audio finalizada")

            # ✅ AGREGAR: Eliminar archivo de audio grabado
            try:
                audio_filename = f"sesion_{self.id_sesion}_audio.wav"
                audio_file_path = os.path.join(os.getcwd(), audio_filename)

                if os.path.exists(audio_file_path):
                    os.remove(audio_file_path)
                    logging.info(
                        f"Archivo de audio eliminado: {audio_filename}")
                else:
                    logging.warning(
                        f"Archivo de audio no encontrado: {audio_filename}")

            except Exception as e:
                logging.error(f"Error eliminando archivo de audio: {e}")

            # SIMULADO: Detener grabación de cámara

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
