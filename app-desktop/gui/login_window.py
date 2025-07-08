from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget
import logging
from ldap3.core.exceptions import LDAPSocketOpenError, LDAPBindError
from services.login_service import LoginService
from services.config_service import ConfigService
from services.utils import load_stylesheet  # ✅ Importar load_stylesheet
from gui.base_window import BaseWindow
from gui.config_window import ConfigWindow

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ConfigPageWrapper(BaseWindow):
    """Wrapper para integrar ConfigWindow en el stack con botón de regreso"""

    def __init__(self, config_service, parent_window):
        super().__init__("SEMEFO - Configuración")  # Usa BaseWindow
        self.config_service = config_service
        self.parent_window = parent_window
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Header con título y botón de regreso al mismo nivel
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignVCenter)

        back_button = QPushButton("← Volver al Login")
        back_button.setProperty("class", "cancel-button")
        back_button.setFixedSize(130, 40)
        back_button.clicked.connect(self.parent_window.show_login)

        title_label = QLabel("Configuración del Sistema")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)

        spacer = QLabel()
        spacer.setFixedSize(130, 40)

        header_layout.addWidget(back_button)
        header_layout.addWidget(title_label, 1)
        header_layout.addWidget(spacer)

        self.config_window = ConfigWindow(self.config_service)

        # Ocultar el título del ConfigWindow ya que está en el header
        config_layout = self.config_window.layout()
        if config_layout and config_layout.count() > 0:
            for i in range(config_layout.count()):
                item = config_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QLabel):
                    label = item.widget()
                    if label.text() == "Configuración del Sistema":
                        label.hide()
                        break

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.config_window)
        self.setLayout(main_layout)

        # ✅ Usar la función load_stylesheet de utils.py
        load_stylesheet(self)

    def closeEvent(self, event):
        # Sobrescribir el evento de cierre para manejar la navegación
        self.parent_window.show_login()
        event.ignore()  # Ignorar el evento de cierre para que la ventana no se cierre


class LoginWindow(BaseWindow):
    def __init__(self, config_service=None):
        super().__init__("SEMEFO - Login")  # Usa BaseWindow
        self.config_service = config_service
        self.login_service = LoginService(config_service)
        self.config_wrapper = None
        self.init_ui()
        self.check_configuration_on_startup()

    def init_ui(self):
        self.stacked_widget = QStackedWidget()

        # Crear solo la página de login inicialmente
        self.login_page = self.create_login_page()
        self.stacked_widget.addWidget(self.login_page)

        # Usar método de la clase base
        self.setup_layout_without_header(self.stacked_widget)

    def create_login_page(self):
        page = QWidget()
        self.label_user = QLabel("Usuario:")
        self.input_user = QLineEdit()
        self.input_user.setText("forense1")
        self.label_pass = QLabel("Contraseña:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.setText("Pi$to01")
        self.button_login = QPushButton("Iniciar Sesión")
        self.button_login.setProperty("class", "action-button")
        self.button_login.clicked.connect(self.login)
        self.button_config = QPushButton("⚙")
        self.button_config.setProperty("class", "settings")
        self.button_config.setFixedSize(50, 50)
        self.button_config.setToolTip("Configuración")
        self.button_config.clicked.connect(self.show_config)
        self.label_logo = QLabel("Logotipo")
        self.label_logo.setPixmap(QPixmap(u"logo.png"))
        self.label_logo.setAlignment(Qt.AlignCenter)
        self.config_status_label = QLabel()
        self.config_status_label.setAlignment(Qt.AlignCenter)
        self.config_status_label.setStyleSheet(
            "font-size: 12px; margin-top: 10px;")
        main_layout = QHBoxLayout()
        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(15)
        form_layout.addWidget(self.label_logo)
        form_layout.addWidget(self.label_user)
        form_layout.addWidget(self.input_user)
        form_layout.addWidget(self.label_pass)
        form_layout.addWidget(self.input_pass)
        form_layout.addWidget(self.button_login)
        form_layout.addWidget(self.config_status_label)
        main_layout.addStretch()
        main_layout.addLayout(form_layout)
        main_layout.addStretch()
        absolute_layout = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addStretch()
        top_row.addWidget(self.button_config)
        absolute_layout.addLayout(top_row)
        absolute_layout.addLayout(main_layout)
        page.setLayout(absolute_layout)
        return page

    def check_configuration_on_startup(self):
        try:
            if not self.config_service:
                self.show_config_warning(
                    "Servicio de configuración no disponible")
                return
            config = self.config_service.load_config()
            if not config:
                self.show_config_warning("No hay configuración guardada")
                return
            ldap_server = config.get('ldap_server', '').strip()
            ldap_domain = config.get('ldap_domain', '').strip()
            if not ldap_server or not ldap_domain:
                self.show_config_warning("Configuración LDAP incompleta")
                return
            self.show_config_ok()
        except Exception as e:
            logging.error(f"Error verificando configuración: {e}")
            self.show_config_warning("Error verificando configuración")

    def show_config_warning(self, message):
        self.config_status_label.setText(
            f"⚠️ {message}\nHaz clic en ⚙ para configurar")
        self.config_status_label.setStyleSheet(
            "color: #ff6b35; font-size: 12px; margin-top: 10px;")
        self.button_login.setEnabled(False)
        self.button_login.setStyleSheet(
            "background-color: #cccccc; color: #666666;")
        self.button_login.setText("Configurar primero")
        logging.warning(f"Configuración requerida: {message}")

    def show_config_ok(self):
        try:
            config = self.config_service.load_config()
            ldap_server = config.get('ldap_server', 'No configurado')
            self.config_status_label.setText(f"✅ Servidor LDAP: {ldap_server}")
            self.config_status_label.setStyleSheet(
                "color: #28a745; font-size: 12px; margin-top: 10px;")
            self.button_login.setEnabled(True)
            self.button_login.setStyleSheet("")
            self.button_login.setText("Iniciar Sesión")
            logging.info(f"Configuración OK - Servidor LDAP: {ldap_server}")
        except Exception as e:
            logging.error(f"Error mostrando estado de configuración: {e}")

    def show_config(self):
        try:
            if self.config_service is None:
                QMessageBox.warning(
                    self, "Error", "Servicio de configuración no disponible")
                return
            if self.stacked_widget.count() == 1:
                self.config_wrapper = ConfigPageWrapper(
                    self.config_service, self)
                self.stacked_widget.addWidget(self.config_wrapper)
            self.stacked_widget.setCurrentIndex(1)
            logging.info("Mostrando configuración integrada en login")
        except Exception as e:
            logging.error(f"Error mostrando configuración: {e}")
            QMessageBox.critical(
                self, "Error", f"Error al mostrar configuración: {str(e)}")

    def show_login(self):
        self.stacked_widget.setCurrentIndex(0)
        self.check_configuration_on_startup()
        logging.info("Regresando a página de login")

    def login(self):
        if not self.button_login.isEnabled():
            QMessageBox.warning(self, "Configuración requerida",
                                "Por favor configure el servidor LDAP antes de iniciar sesión.\n\nHaga clic en el botón ⚙ para configurar.")
            return
        username = self.input_user.text()
        password = self.input_pass.text()
        if not username or not password:
            QMessageBox.warning(self, "Campos requeridos",
                                "Por favor ingrese usuario y contraseña.")
            return
        try:
            success, user_info, error_message = self.login_service.authenticate_user(
                username, password)
            if success:
                logging.info(
                    f"Usuario {username} autenticado correctamente usando configuración centralizada.")
                self.open_expediente_window(user_info['displayName'])
            else:
                QMessageBox.critical(
                    self, "Error de Autenticación", error_message)
                logging.warning(f"Usuario {username} falló autenticación.")
        except (LDAPSocketOpenError, LDAPBindError) as e:
            QMessageBox.critical(self, "LDAP Error", str(e))
            logging.error(f"LDAP Error: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error inesperado", str(e))
            logging.error(f"Error inesperado login: {e}")

    def open_expediente_window(self, medico_nombre):
        from .expediente_window import ExpedienteWindow
        self.expediente_window = ExpedienteWindow(
            medico_nombre=medico_nombre, config_service=self.config_service)
        self.expediente_window.show()
        self.close()
