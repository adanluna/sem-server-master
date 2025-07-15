from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
import os


class LoginFormWidget(QWidget):
    login_requested = Signal(str, str)  # username, password

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        # ✅ CORREGIR: Logo con ruta correcta
        self.logo_label = QLabel("Logotipo")

        # ✅ Calcular ruta correcta desde gui/components/ hacia app-desktop/
        current_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))  # Subir 3 niveles
        logo_path = os.path.join(current_dir, "logo.png")

        print(f"🔍 DEBUG LoginForm: Buscando logo en: {logo_path}")

        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            scaled_pixmap = logo_pixmap.scaled(
                80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
            print(f"✅ Logo cargado en LoginForm desde: {logo_path}")
        else:
            print(f"❌ Logo no encontrado en LoginForm: {logo_path}")
            # ✅ Fallback: Mostrar texto estilizado
            self.logo_label.setText("🏛️ SEMEFO")
            self.logo_label.setStyleSheet("""
                font-size: 24px; 
                font-weight: bold; 
                color: #2c3e50;
                padding: 10px;
            """)

        self.logo_label.setAlignment(Qt.AlignCenter)

        # Campos
        self.user_label = QLabel("Usuario:")
        self.user_input = QLineEdit()
        self.user_input.setText("forense1")
        self.user_input.setFixedWidth(250)

        self.pass_label = QLabel("Contraseña:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setText("Pi$to01")
        self.pass_input.setFixedWidth(250)

        # Botón
        self.login_button = QPushButton("Iniciar Sesión")
        self.login_button.setProperty("class", "action-button")
        self.login_button.setFixedWidth(250)
        self.login_button.clicked.connect(self.on_login_clicked)

        # Conectar Enter para login
        self.user_input.returnPressed.connect(self.on_login_clicked)
        self.pass_input.returnPressed.connect(self.on_login_clicked)

        # Agregar al layout
        layout.addWidget(self.logo_label)
        layout.addWidget(self.user_label)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_label)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def on_login_clicked(self):
        username = self.user_input.text()
        password = self.pass_input.text()
        self.login_requested.emit(username, password)

    def set_button_enabled(self, enabled):
        self.login_button.setEnabled(enabled)

    def set_button_text(self, text):
        self.login_button.setText(text)

    def set_button_tooltip(self, tooltip):
        self.login_button.setToolTip(tooltip)

    def get_credentials(self):
        """Obtener credenciales actuales"""
        return self.user_input.text(), self.pass_input.text()

    def clear_password(self):
        """Limpiar campo de contraseña"""
        self.pass_input.clear()

    def focus_username(self):
        """Enfocar campo de usuario"""
        self.user_input.setFocus()

    def focus_password(self):
        """Enfocar campo de contraseña"""
        self.pass_input.setFocus()
