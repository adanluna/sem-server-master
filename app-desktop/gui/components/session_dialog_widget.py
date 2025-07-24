from services.api_service import ApiService
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal


class SessionDialogWidget(QDialog):
    session_close_requested = Signal(dict, str)  # session_data, username

    def __init__(self, session_data, username, api_client, parent=None):
        super().__init__(parent)
        print(session_data)
        self.session_data = session_data
        self.username = username
        self.api_client = api_client
        self.id_sesion = session_data.get('id')
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Sesión Activa Encontrada")
        self.setModal(True)
        self.resize(450, 300)

        layout = QVBoxLayout()

        # Título
        title_label = QLabel("⚠️ Sesión Activa Detectada")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #ff6b35;")
        layout.addWidget(title_label)

        # Info de la sesión
        info_text = self.create_info_text()
        self.info_label = QLabel(info_text)
        self.info_label.setStyleSheet(
            "font-size: 12px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;"
        )
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Botones
        self.button_layout = QHBoxLayout()

        self.close_button = QPushButton("🚪 Cerrar Sesión Activa")
        self.close_button.setProperty("class", "danger-button")
        self.close_button.clicked.connect(self.on_close_session)

        self.cancel_button = QPushButton("❌ Cancelar Login")
        self.cancel_button.setProperty("class", "secondary")
        self.cancel_button.clicked.connect(self.reject)

        self.button_layout.addWidget(self.close_button)
        self.button_layout.addWidget(self.cancel_button)
        layout.addLayout(self.button_layout)

        self.setLayout(layout)

    def create_info_text(self):
        expediente = self.session_data.get('numero_expediente', 'N/A')
        nombre_sesion = self.session_data.get('nombre_sesion', 'N/A')
        plancha = self.session_data.get('plancha_id', 'N/A')
        tablet = self.session_data.get('tablet_id', 'N/A')
        return f"""
El usuario '{self.username}' tiene una sesión activa en curso:

📁 Expediente: {expediente}
🎯 Sesión: {nombre_sesion}
🏥 Plancha: {plancha}
📱 Tablet: {tablet}

Debe cerrar la sesión activa antes de continuar.
"""

    def on_close_session(self):
        try:
            id_sesion = self.session_data.get("id_sesion")
            numero_expediente = self.session_data.get("numero_expediente")
            print("DEBUG id_sesion:", id_sesion)
            print("DEBUG numero_expediente:", numero_expediente)

            if not id_sesion or not numero_expediente:
                raise Exception("Faltan datos de sesión para procesar.")

            # 1. Procesar la sesión (envía expediente y id_sesion)
            self.api_client.procesar_sesion(numero_expediente, id_sesion)
            # 2. Finalizar la sesión (solo id_sesion)
            self.api_client.finalizar_sesion(id_sesion)

            self.info_label.setText(
                "✅ Sesión enviada a procesar.\n\nPresiona 'Aceptar' para regresar al login.")
            self.info_label.show()
            for i in reversed(range(self.button_layout.count())):
                widget = self.button_layout.itemAt(i).widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)
            aceptar_btn = QPushButton("Aceptar")
            aceptar_btn.setProperty("class", "action-button")
            aceptar_btn.clicked.connect(self.accept)
            self.button_layout.addWidget(aceptar_btn)
            aceptar_btn.show()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al finalizar sesión: {e}")

    def set_close_button_enabled(self, enabled):
        self.close_button.setEnabled(enabled)

    def set_close_button_text(self, text):
        self.close_button.setText(text)

    def show_success_and_accept(self):
        self.accept()
