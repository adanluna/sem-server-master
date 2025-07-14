from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal


class SessionDialogWidget(QDialog):
    session_close_requested = Signal(dict, str)  # session_data, username

    def __init__(self, session_data, username, parent=None):
        super().__init__(parent)
        self.session_data = session_data
        self.username = username
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
        info_label = QLabel(info_text)
        info_label.setStyleSheet(
            "font-size: 12px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Botones
        button_layout = QHBoxLayout()

        self.close_button = QPushButton("🚪 Cerrar Sesión Activa")
        self.close_button.setProperty("class", "danger-button")
        self.close_button.clicked.connect(self.on_close_session)

        self.cancel_button = QPushButton("❌ Cancelar Login")
        self.cancel_button.setProperty("class", "secondary")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.close_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_info_text(self):
        expediente = self.session_data.get('numero_expediente', 'N/A')
        nombre_sesion = self.session_data.get('nombre_sesion', 'N/A')
        plancha = self.session_data.get(
            'plancha_id', 'N/A')    # Usar 'plancha_id'
        tablet = self.session_data.get(
            'tablet_id', 'N/A')     # Usar 'tablet_id'

        # Debug para verificar datos
        print(f"🔍 DEBUG SessionDialog - Datos recibidos: {self.session_data}")
        print(f"🔍 DEBUG SessionDialog - Expediente: {expediente}")
        print(f"🔍 DEBUG SessionDialog - Sesión: {nombre_sesion}")
        print(f"🔍 DEBUG SessionDialog - Plancha: {plancha}")
        print(f"🔍 DEBUG SessionDialog - Tablet: {tablet}")

        return f"""
El usuario '{self.username}' tiene una sesión activa en curso:

📁 Expediente: {expediente}
🎯 Sesión: {nombre_sesion}
🏥 Plancha: {plancha}
📱 Tablet: {tablet}

Debe cerrar la sesión activa antes de continuar.
"""

    def on_close_session(self):
        self.session_close_requested.emit(self.session_data, self.username)

    def set_close_button_enabled(self, enabled):
        """Habilitar/deshabilitar botón de cerrar sesión"""
        self.close_button.setEnabled(enabled)

    def set_close_button_text(self, text):
        """Cambiar texto del botón de cerrar sesión"""
        self.close_button.setText(text)

    def show_success_and_accept(self):
        """Mostrar éxito y cerrar diálogo"""
        self.accept()
