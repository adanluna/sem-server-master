from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget
from PySide6.QtCore import Qt
import logging
from services.utils import load_stylesheet
from gui.base_window import BaseWindowWithHeader
# Asegúrate de que la ruta sea correcta
from gui.success_window import SuccessWindow

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class GrabarWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre, numero_expediente, nombre_sesion, config_service):
        super().__init__(
            medico_nombre=medico_nombre,
            numero_expediente=numero_expediente,
            nombre_sesion=nombre_sesion,
            config_service=config_service,
            window_title="SEMEFO - Grabación"
        )
        self.init_ui()

    def init_ui(self):
        self.stacked_widget = QStackedWidget()
        self.page_grabar = self.create_grabar_page()
        self.page_status = self.create_status_page()
        self.stacked_widget.addWidget(self.page_grabar)
        self.stacked_widget.addWidget(self.page_status)

        # Usar método de la clase base
        self.setup_content(self.stacked_widget)

    def create_grabar_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        status_label = QLabel("🟢 Cámaras activas | 🎙️ Micrófono activo")
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setProperty("class", "status-text")

        self.status_text = QLabel("Grabando")
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setProperty("class", "recording-status")

        self.pause_btn = QPushButton("Pausar Grabación")
        self.pause_btn.setProperty("class", "cancel-button")
        self.pause_btn.setFixedSize(200, 60)
        self.pause_btn.clicked.connect(self.pause_recording)

        self.save_btn = QPushButton("Guardar Grabación")
        self.save_btn.setProperty("class", "action-button")
        self.save_btn.setFixedSize(200, 60)
        self.save_btn.clicked.connect(self.save_recording)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.pause_btn)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addStretch()

        self.timer_label = QLabel("Grabación: 00:00:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setProperty("class", "timer-label")

        layout.addWidget(status_label)
        layout.addWidget(self.status_text)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.timer_label)
        page.setLayout(layout)

        return page

    def create_status_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Estado de la Grabación")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        page.setLayout(layout)
        return page

    def pause_recording(self):
        if self.status_text.text() == "Grabando":
            logging.info("Grabación pausada")
            self.status_text.setText("Pausada")
            QMessageBox.information(self, "Pausa", "Grabación en pausa.")
            self.pause_btn.setText("Continuar Grabación")
            self.pause_btn.setProperty("class", "action-button")
            load_stylesheet(self.pause_btn)
            self.save_btn.hide()
        else:
            logging.info("Grabación reanudada")
            self.status_text.setText("Grabando")
            self.pause_btn.setText("Pausar Grabación")
            self.pause_btn.setProperty("class", "cancel-button")
            load_stylesheet(self.pause_btn)
            self.save_btn.show()

    def save_recording(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Guardar Grabación")
        msg_box.setText(
            "¿Estás seguro que quieres terminar la grabación y guardarla?")
        msg_box.setIcon(QMessageBox.Question)
        yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
        yes_button.setProperty("class", "action-button")
        no_button = msg_box.addButton("No", QMessageBox.NoRole)
        no_button.setProperty("class", "cancel-button")
        msg_box.setDefaultButton(no_button)
        load_stylesheet(msg_box)
        reply = msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            logging.info("Grabación guardada")
            self.open_success()

    def open_success(self):
        self.success_window = SuccessWindow(self.medico_nombre, self.numero_expediente, self.nombre_sesion,
                                            self.timer_label.text().replace("Grabación: ", ""), self.config_service)
        self.success_window.show()
        self.close()
