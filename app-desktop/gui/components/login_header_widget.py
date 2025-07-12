from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal


class LoginHeaderWidget(QWidget):
    config_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.addStretch()

        # Botón configuración
        self.config_button = QPushButton("⚙")
        self.config_button.setProperty("class", "settings")
        self.config_button.setFixedSize(50, 50)
        self.config_button.setToolTip("Configuración")
        self.config_button.clicked.connect(self.config_requested.emit)

        layout.addWidget(self.config_button)
        self.setLayout(layout)

    def set_config_enabled(self, enabled):
        """Habilitar/deshabilitar botón de configuración"""
        self.config_button.setEnabled(enabled)
