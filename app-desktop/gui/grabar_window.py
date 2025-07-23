from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSpacerItem, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from gui.base_window import BaseWindowWithHeader
from services.api_client import ApiClient
from services.audio_recorder import AudioRecorder
import logging
import os
import requests


class GrabarWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre="", numero_expediente="", nombre_sesion="",
                 id_sesion=None, config_service=None, username_ldap=""):
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
        self.is_recording = False
        self.is_paused = False
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_timer)
        self.recording_time = 0
        self.init_ui()

    def init_ui(self):
        if self.content_widget.layout() is None:
            layout = QVBoxLayout()
            self.content_widget.setLayout(layout)
        else:
            layout = self.content_widget.layout()

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        BUTTON_WIDTH = 200
        BUTTON_HEIGHT = 150
        BUTTON_SPACING = 20

        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(40)

        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.status_label = QLabel("Listo para iniciar grabación")
        self.status_label.setProperty("class", "recording-status")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(60)
        self.status_label.setMinimumWidth(400)
        layout.addWidget(self.status_label)

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setProperty("class", "timer-label")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFixedHeight(50)
        self.timer_label.setMinimumWidth(200)
        layout.addWidget(self.timer_label)

        button_container = QWidget()
        button_container.setFixedHeight(200)
        button_container_layout = QVBoxLayout(button_container)
        button_container_layout.setSpacing(20)
        button_container_layout.setAlignment(Qt.AlignCenter)

        self.button_start = QPushButton("🔴\nIniciar\nGrabación")
        self.button_start.setProperty("class", "start-button")
        self.button_start.clicked.connect(self.start_recording)
        self.button_start.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        button_container_layout.addWidget(
            self.button_start, alignment=Qt.AlignCenter)

        self.button_pause = QPushButton("⏸\nPausar")
        self.button_pause.setProperty("class", "pause-button")
        self.button_pause.clicked.connect(self.pause_recording)
        self.button_pause.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.button_pause.setVisible(False)

        self.button_continue = QPushButton("▶️\nContinuar")
        self.button_continue.setProperty("class", "continue-button")
        self.button_continue.clicked.connect(self.continue_recording)
        self.button_continue.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.button_continue.setVisible(False)

        self.button_finish = QPushButton("✅\nFinalizar")
        self.button_finish.setProperty("class", "finish-button")
        self.button_finish.clicked.connect(self.finish_session)
        self.button_finish.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.button_finish.setVisible(False)

        horizontal_buttons_layout = QHBoxLayout()
        horizontal_buttons_layout.setSpacing(BUTTON_SPACING)
        horizontal_buttons_layout.setAlignment(Qt.AlignCenter)
        horizontal_buttons_layout.addWidget(self.button_pause)
        horizontal_buttons_layout.addWidget(self.button_continue)
        horizontal_buttons_layout.addWidget(self.button_finish)

        button_container_layout.addLayout(horizontal_buttons_layout)
        layout.addWidget(button_container, alignment=Qt.AlignCenter)

        layout.addItem(QSpacerItem(
            20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def start_recording(self):
        try:
            audio_filename = f"sesion_{self.id_sesion}_audio.wav"
            if self.audio_recorder.start_recording(audio_filename):
                logging.info("Grabación de audio iniciada")
            else:
                QMessageBox.warning(
                    self, "Error", "No se pudo iniciar la grabación de audio")
                return
            self.is_recording = True
            self.is_paused = False
            self.button_start.setVisible(False)
            self.button_pause.setVisible(True)
            self.button_continue.setVisible(False)
            self.button_finish.setVisible(True)
            self.status_label.setText("🔴 Grabando...")
            self.recording_time = 0
            self.recording_timer.start(1000)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error iniciando grabación: {str(e)}")
            logging.error(f"Error iniciando grabación: {e}")

    def pause_recording(self):
        self.recording_timer.stop()
        self.is_paused = True
        self.button_start.setVisible(False)
        self.button_pause.setVisible(False)
        self.button_continue.setVisible(True)
        self.button_finish.setVisible(True)
        self.status_label.setText("⏸ Grabación pausada")

    def continue_recording(self):
        self.is_paused = False
        self.button_start.setVisible(False)
        self.button_pause.setVisible(True)
        self.button_continue.setVisible(False)
        self.button_finish.setVisible(True)
        self.status_label.setText("🔴 Grabando...")
        self.recording_timer.start(1000)

    def finish_session(self):
        was_recording = self.is_recording and not self.is_paused
        if was_recording:
            self.recording_timer.stop()
            if hasattr(self.audio_recorder, 'pause_recording'):
                self.audio_recorder.pause_recording()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Finalizar Sesión")
        msg_box.setText("¿Está seguro de que desea finalizar la sesión?")
        msg_box.setIcon(QMessageBox.Question)
        no_button = msg_box.addButton("No", QMessageBox.NoRole)
        yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
        msg_box.setDefaultButton(no_button)
        result = msg_box.exec()

        if msg_box.clickedButton() == no_button:
            if was_recording:
                self.audio_recorder.resume_recording()
                self.recording_timer.start(1000)
            return
        if msg_box.clickedButton() != yes_button:
            return

        self.recording_timer.stop()
        self.audio_recorder.stop_recording()

        try:
            audio_file = f"sesion_{self.id_sesion}_audio.wav"
            if os.path.exists(audio_file):
                os.remove(audio_file)
                print(f"🗑️ Archivo temporal eliminado: {audio_file}")
        except Exception as e:
            logging.error(f"Error al eliminar archivo temporal: {e}")

        # ✅ Ahora solo lanzar procesamiento
        try:
            self.api_client.procesar_sesion(
                self.numero_expediente, self.id_sesion)
            logging.info(
                f"🚀 Sesión enviada a procesamiento: {self.numero_expediente}/{self.id_sesion}")
        except Exception as e:
            logging.error(f"💥 Error enviando sesión a procesamiento: {e}")

        # ✅ Finalizar sesión en backend
        try:
            self.api_client.finalizar_sesion(self.id_sesion)
            logging.info(f"✅ Sesión {self.id_sesion} finalizada en backend")
        except Exception as e:
            logging.error(f"💥 Error finalizando sesión en API: {e}")

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

    def update_timer(self):
        self.recording_time += 1
        hours = self.recording_time // 3600
        minutes = (self.recording_time % 3600) // 60
        seconds = self.recording_time % 60
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
