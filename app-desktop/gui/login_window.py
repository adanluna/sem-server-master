from PySide6.QtCore import (
    QRect, Qt
)
from PySide6.QtGui import (
    QPixmap)
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget
import sys
import logging
from services.login_service import LoginService
from services.config_service import ConfigService


class LoginWindow(QWidget):
    def __init__(self, config_service):
        super().__init__()
        self.config_service = config_service
        self.login_service = LoginService()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SEMEFO")
        self.resize(853, 522)

        # Crear el widget apilado para alternar entre vistas
        self.stacked_widget = QStackedWidget()

        # Crear las páginas
        self.login_page = self.create_login_page()
        self.config_page = self.create_config_page()

        # Agregar las páginas al stack
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.config_page)

        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        # Cargar estilos CSS desde la raíz del proyecto
        import os
        styles_path = os.path.join(os.path.dirname(
            __file__), "..", "..", "styles.qss")
        try:
            with open(styles_path, "r") as f:
                self.setStyleSheet(f.read())
                print("✅ Estilos cargados correctamente")
        except FileNotFoundError:
            print(f"❌ Archivo de estilos no encontrado en: {styles_path}")

    def create_login_page(self):
        page = QWidget()

        self.label_user = QLabel("Usuario:")
        self.input_user = QLineEdit()

        self.label_pass = QLabel("Contraseña:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)

        self.button_login = QPushButton("Iniciar Sesión")
        self.button_login.clicked.connect(self.login)

        self.button_config = QPushButton("⚙")
        self.button_config.clicked.connect(self.show_config_page)
        self.button_config.setProperty("class", "settings")
        self.button_config.setFixedSize(50, 50)
        self.button_config.setToolTip("Configuración")

        self.label_logo = QLabel("Logotipo")
        self.label_logo.setPixmap(QPixmap(u"logo.png"))
        self.label_logo.setAlignment(Qt.AlignCenter)

        # Layout principal con elementos centrados
        main_layout = QHBoxLayout()

        # Layout vertical para los elementos del formulario
        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(15)

        # Agregar elementos al layout del formulario
        form_layout.addWidget(self.label_logo)
        form_layout.addWidget(self.label_user)
        form_layout.addWidget(self.input_user)
        form_layout.addWidget(self.label_pass)
        form_layout.addWidget(self.input_pass)
        form_layout.addWidget(self.button_login)

        # Centrar el formulario en el layout principal
        main_layout.addStretch()
        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Layout para el botón de configuración en la esquina superior derecha
        absolute_layout = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addStretch()
        top_row.addWidget(self.button_config)
        absolute_layout.addLayout(top_row)
        absolute_layout.addLayout(main_layout)

        page.setLayout(absolute_layout)
        return page

    def create_config_page(self):
        page = QWidget()

        # Botón para volver al login
        self.button_back = QPushButton("← Volver")
        self.button_back.clicked.connect(self.show_login_page)
        self.button_back.setProperty("class", "secondary")

        # Campos de configuración
        self.input_planch = QLineEdit()
        self.input_camera1 = QLineEdit()
        self.input_camera2 = QLineEdit()
        self.input_api = QLineEdit()

        self.button_save = QPushButton("Guardar")
        self.button_save.clicked.connect(self.save_config)

        # Layout principal con elementos centrados
        main_layout = QHBoxLayout()

        # Layout vertical para los elementos del formulario
        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(15)

        # Agregar elementos al layout del formulario
        title_label = QLabel("Configuración de la Plancha")
        title_label.setProperty("class", "title")
        title_label.setAlignment(Qt.AlignCenter)

        form_layout.addWidget(title_label)
        form_layout.addWidget(QLabel("Nombre de Plancha:"))
        form_layout.addWidget(self.input_planch)
        form_layout.addWidget(QLabel("IP Cámara 1:"))
        form_layout.addWidget(self.input_camera1)
        form_layout.addWidget(QLabel("IP Cámara 2:"))
        form_layout.addWidget(self.input_camera2)
        form_layout.addWidget(QLabel("IP API Server:"))
        form_layout.addWidget(self.input_api)
        form_layout.addWidget(self.button_save)

        # Centrar el formulario en el layout principal
        main_layout.addStretch()
        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Layout para el botón de volver en la esquina superior izquierda
        absolute_layout = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addWidget(self.button_back)
        top_row.addStretch()
        absolute_layout.addLayout(top_row)
        absolute_layout.addLayout(main_layout)

        page.setLayout(absolute_layout)

        # Cargar configuración existente
        self.load_config()

        return page

    def show_config_page(self):
        self.stacked_widget.setCurrentIndex(1)

    def show_login_page(self):
        self.stacked_widget.setCurrentIndex(0)

    def load_config(self):
        config = self.config_service.load_config()
        if config:
            self.input_planch.setText(config.get('planch', ''))
            self.input_camera1.setText(config.get('camera1', ''))
            self.input_camera2.setText(config.get('camera2', ''))
            self.input_api.setText(config.get('api', ''))

    def save_config(self):
        data = {
            'planch': self.input_planch.text(),
            'camera1': self.input_camera1.text(),
            'camera2': self.input_camera2.text(),
            'api': self.input_api.text()
        }
        self.config_service.save_config(data)
        QMessageBox.information(
            self, "Guardado", "Configuración guardada exitosamente.")
        self.show_login_page()  # Volver al login después de guardar

    def login(self):
        username = self.input_user.text()
        password = self.input_pass.text()

        # Validar que se ingresaron datos
        if not username or not password:
            QMessageBox.warning(
                self, "Campos requeridos", "Por favor ingrese usuario y contraseña.")
            return

        success, user_info, error_message = self.login_service.authenticate_user(
            username, password)

        if success:
            QMessageBox.information(
                self, "Login Exitoso", f"Bienvenido {user_info['displayName']}")
        else:
            QMessageBox.critical(
                self, "Error de Autenticación", error_message)
