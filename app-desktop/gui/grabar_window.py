import os
import shutil
import requests
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSpacerItem, QSizePolicy, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from gui.base_window import BaseWindowWithHeader
from services.api_client import ApiClient
from services.audio_recorder import AudioRecorder
from services.video_recorder import VideoRecorder
import logging


class GrabarWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre="", numero_expediente="", nombre_sesion="", config_service=None, id_sesion=None):
        super().__init__(
            medico_nombre=medico_nombre,
            numero_expediente=numero_expediente,
            nombre_sesion=nombre_sesion,
            config_service=config_service,
            window_title="SEMEFO - Grabación"
        )
        self.api_client = ApiClient(config_service)
        self.id_sesion = id_sesion
        self.audio_recorder = AudioRecorder()
        self.video_recorder = VideoRecorder()
        self.is_recording = False
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_timer)
        self.recording_time = 0
        self.init_ui()

    def init_ui(self):
        # Layout principal para el contenido
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Espaciador superior
        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Título
        title_label = QLabel("Grabación de Sesión")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Estado de grabación
        self.status_label = QLabel("Listo para grabar")
        self.status_label.setProperty("class", "recording-status")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Timer
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setProperty("class", "timer-label")
        self.timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.timer_label)

        # Botones de control
        button_layout = QHBoxLayout()
        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.button_record = QPushButton("🔴 Iniciar Grabación")
        self.button_record.setProperty("class", "action-button")
        self.button_record.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.button_record)

        self.button_finish = QPushButton("✅ Finalizar y Procesar")
        self.button_finish.setProperty("class", "action-button")
        self.button_finish.clicked.connect(self.finish_session)
        self.button_finish.setEnabled(False)
        button_layout.addWidget(self.button_finish)

        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_layout)

        # Botón cancelar
        cancel_layout = QHBoxLayout()
        cancel_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.button_cancel = QPushButton("❌ Cancelar Sesión")
        self.button_cancel.setProperty("class", "cancel-button")
        self.button_cancel.clicked.connect(self.cancel_session)
        cancel_layout.addWidget(self.button_cancel)

        cancel_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(cancel_layout)

        # Espaciador inferior
        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def toggle_recording(self):
        """Alternar entre iniciar y detener grabación"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Iniciar grabación de audio y video"""
        try:
            # Iniciar grabación de audio
            if self.audio_recorder.start_recording():
                logging.info("Grabación de audio iniciada")
            else:
                QMessageBox.warning(
                    self, "Error", "No se pudo iniciar la grabación de audio")
                return

            # Iniciar grabación de video
            if self.video_recorder.start_recording():
                logging.info("Grabación de video iniciada")
            else:
                QMessageBox.warning(
                    self, "Error", "No se pudo iniciar la grabación de video")
                self.audio_recorder.stop_recording()
                return

            # Actualizar UI
            self.is_recording = True
            self.button_record.setText("⏹ Detener Grabación")
            self.status_label.setText("🔴 Grabando...")
            self.button_cancel.setEnabled(False)

            # Iniciar timer
            self.recording_time = 0
            self.recording_timer.start(1000)  # Actualizar cada segundo

            logging.info(f"Grabación iniciada para sesión {self.id_sesion}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error iniciando grabación: {str(e)}")
            logging.error(f"Error iniciando grabación: {e}")

    def stop_recording(self):
        """Detener grabación"""
        try:
            # Detener timer
            self.recording_timer.stop()

            # Detener grabación de audio
            self.audio_recorder.stop_recording()
            logging.info("Grabación de audio detenida")

            # Detener grabación de video
            self.video_recorder.stop_recording()
            logging.info("Grabación de video detenida")

            # Actualizar UI
            self.is_recording = False
            self.button_record.setText("🔴 Iniciar Grabación")
            self.status_label.setText("⏸ Grabación detenida")
            self.button_finish.setEnabled(True)
            self.button_cancel.setEnabled(True)

            logging.info(f"Grabación detenida para sesión {self.id_sesion}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error deteniendo grabación: {str(e)}")
            logging.error(f"Error deteniendo grabación: {e}")

    def update_timer(self):
        """Actualizar el timer de grabación"""
        self.recording_time += 1
        hours = self.recording_time // 3600
        minutes = (self.recording_time % 3600) // 60
        seconds = self.recording_time % 60
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def finish_session(self):
        """Finalizar sesión y procesar archivos"""
        try:
            # Confirmar finalización
            reply = QMessageBox.question(
                self,
                "Finalizar Sesión",
                "¿Está seguro de que desea finalizar la sesión y enviar los archivos a procesamiento?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # Detener grabación si está activa
            if self.is_recording:
                self.stop_recording()

            # Mostrar ventana de éxito
            from gui.success_window import SuccessWindow
            self.success_window = SuccessWindow(
                self.medico_nombre,
                self.numero_expediente,
                self.nombre_sesion,
                self.config_service,
                self.id_sesion
            )
            self.success_window.show()
            self.close()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error finalizando sesión: {str(e)}")
            logging.error(f"Error finalizando sesión: {e}")

    def cancel_session(self):
        """Cancelar sesión actual"""
        try:
            reply = QMessageBox.question(
                self,
                "Cancelar Sesión",
                "¿Está seguro de que desea cancelar la sesión? Se perderán todos los datos grabados.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Detener grabación si está activa
                if self.is_recording:
                    self.stop_recording()

                # Eliminar archivos temporales
                self.audio_recorder.cleanup()
                self.video_recorder.cleanup()

                # Regresar a ventana de expedientes
                from gui.expediente_window import ExpedienteWindow
                self.expediente_window = ExpedienteWindow(
                    self.medico_nombre, self.config_service)
                self.expediente_window.show()
                self.close()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error cancelando sesión: {str(e)}")
            logging.error(f"Error cancelando sesión: {e}")
