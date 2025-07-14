from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                               QMessageBox, QStackedWidget, QSpacerItem, QSizePolicy, QPushButton)
import logging
from ldap3.core.exceptions import LDAPSocketOpenError, LDAPBindError
from services.login_service import LoginService
from services.api_service import ApiService
from services.utils import load_stylesheet
from .components.services_status_widget import ServicesStatusWidget
from .components.login_form_widget import LoginFormWidget
from .components.login_header_widget import LoginHeaderWidget  # Nombre cambiado
from .components.config_tabs_widget import ConfigTabsWidget
from .components.session_dialog_widget import SessionDialogWidget
from .components.validation_utils import ValidationUtils

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class LoginWindow(QWidget):
    def __init__(self, config_service=None):
        super().__init__()
        self.config_service = config_service
        self.login_service = LoginService(config_service)
        self.api_service = ApiService()

        # Inicializar UI
        self.init_ui()

        # Verificar configuración al inicio
        self.check_configuration_on_startup()

    def init_ui(self):
        # Configuración de la ventana principal
        self.setWindowTitle("SEMEFO - Sistema")
        self.resize(853, 622)
        self.center_window()

        # Aplicar estilos
        load_stylesheet(self)

        # Crear el stacked widget para alternar entre login y config
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

        # Mostrar la página de login por defecto
        self.stacked_widget.setCurrentWidget(self.login_page)

    def center_window(self):
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def create_login_page(self):
        """Crear la página de login usando widgets"""
        page = QWidget()
        main_layout = QVBoxLayout()

        # Header con botón de configuración - usando el nombre correcto
        self.header_widget = LoginHeaderWidget()
        self.header_widget.config_requested.connect(self.show_config)

        # Widget de formulario de login
        self.login_form_widget = LoginFormWidget()
        self.login_form_widget.login_requested.connect(
            self.handle_login_request)

        # Widget de estados de servicios
        self.services_widget = ServicesStatusWidget(self.config_service)

        # Layout principal centrado
        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignCenter)
        content_layout.setSpacing(20)

        # Agregar formulario y servicios
        content_layout.addWidget(self.login_form_widget)
        content_layout.addWidget(self.services_widget)

        main_layout.addWidget(self.header_widget)
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addStretch()

        page.setLayout(main_layout)
        return page

    def create_config_page(self):
        """Crear la página de configuración usando widgets"""
        page = QWidget()
        layout = QVBoxLayout()

        # Header con título y botón de volver
        header_layout = QHBoxLayout()

        # Botón volver
        back_button = QPushButton("Volver al Login")
        back_button.setProperty("class", "secondary-button")
        back_button.clicked.connect(self.show_login)
        header_layout.addWidget(back_button)

        header_layout.addStretch()

        # Título
        title_label = QLabel("Configuración del Sistema SEMEFO")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)

        layout.addLayout(header_layout)
        layout.addWidget(title_label)

        # Widget de tabs de configuración
        self.config_tabs_widget = ConfigTabsWidget(self.config_service)
        layout.addWidget(self.config_tabs_widget)

        # Botones
        button_layout = QHBoxLayout()
        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Botón Guardar
        self.save_button = QPushButton("Guardar Configuración")
        self.save_button.setProperty("class", "success-button")
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)

        # Botón Cancelar
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setProperty("class", "cancel-button")
        self.cancel_button.clicked.connect(self.show_login)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        page.setLayout(layout)
        return page

    def show_config(self):
        """Cambiar a la página de configuración"""
        print("🔍 DEBUG: show_config() - Cambiando a página de configuración")
        self.load_current_config()
        self.stacked_widget.setCurrentWidget(self.config_page)
        self.setWindowTitle("SEMEFO - Configuración")

    def show_login(self):
        """Volver a la página de login desde configuración"""
        print("🔍 DEBUG: show_login() - Cambiando a página de login")
        self.stacked_widget.setCurrentWidget(self.login_page)
        self.setWindowTitle("SEMEFO - Sistema")
        # Actualizar servicios al volver
        self.services_widget.check_all_services()
        self.check_configuration_on_startup()
        logging.info("Regresando a página de login")

    def load_current_config(self):
        """Cargar la configuración actual en los campos"""
        try:
            config = self.config_service.load_config()
            self.config_tabs_widget.load_config_data(config)
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
            QMessageBox.warning(
                self, "Error", f"Error cargando configuración: {str(e)}")

    def save_config(self):
        """Guardar la configuración usando el widget y validation_utils"""
        try:
            # Obtener datos del widget
            config_data = self.config_tabs_widget.get_config_data()

            # Validar usando ValidationUtils
            validation_errors = ValidationUtils.validate_all_config_fields(
                config_data)

            if validation_errors:
                error_message = "\n".join(validation_errors)
                QMessageBox.warning(self, "Errores de Validación",
                                    f"Se encontraron los siguientes errores:\n\n{error_message}")
                return

            # Guardar configuración
            if self.config_service.save_config(config_data):
                QMessageBox.information(
                    self, "Éxito", "Configuración guardada correctamente")
                # Actualizar servicios después de guardar
                self.services_widget.check_all_services()
                # Volver al login
                self.show_login()
            else:
                QMessageBox.critical(
                    self, "Error", "Error al guardar la configuración")

        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")

    def check_configuration_on_startup(self):
        """Verificar configuración al inicio"""
        try:
            if not self.config_service:
                self.show_config_warning(
                    "Servicio de configuración no disponible")
                return

            config = self.config_service.load_config()
            if not config:
                self.show_config_warning("Archivo config.json no encontrado")
                return

            # Validar configuración completa usando ValidationUtils
            validation_errors = ValidationUtils.validate_configuration(config)
            if validation_errors:
                self.show_config_warning(
                    f"Configuración incompleta: {', '.join(validation_errors)}")
                return

            # Si la configuración está completa, verificar servicios
            self.check_login_availability()

        except Exception as e:
            logging.error(f"Error verificando configuración: {e}")
            self.show_config_warning("Error al verificar configuración")

    def check_login_availability(self):
        """Verificar si el login debe estar habilitado"""
        if self.services_widget.are_all_services_ok():
            self.enable_login()
        else:
            self.disable_login_services()

    def show_config_warning(self, message):
        """Mostrar advertencia de configuración y deshabilitar login"""
        self.login_form_widget.set_button_enabled(False)
        self.login_form_widget.set_button_text("Configurar primero")
        self.login_form_widget.set_button_tooltip(
            f"Completar configuración: {message}")
        logging.warning(f"Configuración requerida: {message}")

    def disable_login_services(self):
        """Deshabilitar login por servicios no disponibles"""
        self.login_form_widget.set_button_enabled(False)
        self.login_form_widget.set_button_text("Servicios no disponibles")
        self.login_form_widget.set_button_tooltip(
            "Todos los servicios (LDAP, API, RabbitMQ) deben estar activos")
        logging.warning("Login deshabilitado: servicios no disponibles")

    def enable_login(self):
        """Habilitar login cuando todo está correcto"""
        self.login_form_widget.set_button_enabled(True)
        self.login_form_widget.set_button_text("Iniciar Sesión")
        self.login_form_widget.set_button_tooltip("")
        logging.info("Login habilitado: configuración y servicios OK")

    def handle_login_request(self, username, password):
        """Manejar solicitud de login desde el widget"""
        print("🔍 DEBUG: Entrando a función handle_login_request()")

        if not username or not password:
            QMessageBox.warning(self, "Campos requeridos",
                                "Por favor ingrese usuario y contraseña.")
            return

        try:
            # 1. PRIMERO verificar sesiones pendientes
            print("🔍 DEBUG: Verificando sesiones pendientes...")
            session_response = self.login_service.check_pending_session(
                username)

            if session_response:  # Si hay sesión pendiente
                print("⚠️ DEBUG: Sesión pendiente encontrada, mostrando diálogo")
                self.show_pending_session_dialog(session_response, username)
                return  # Detener el flujo aquí

            print("✅ DEBUG: No hay sesiones pendientes, continuando con autenticación...")

            # 2. Proceder con autenticación LDAP
            print("🔍 DEBUG: Iniciando autenticación LDAP...")
            auth_result = self.login_service.authenticate_user(
                username, password)

            if not auth_result['success']:
                QMessageBox.critical(
                    self, "Error de Autenticación", auth_result['error'])
                logging.warning(
                    f"Usuario {username} falló autenticación: {auth_result['error']}")
                return

            logging.info(f"Usuario {username} autenticado correctamente.")

            # 3. Abrir expedientes con los datos del usuario
            user_info = auth_result['user_data']
            self.open_expediente_window(
                user_info['displayName'],
                username  # ✅ Pasar también el username LDAP
            )

        except Exception as e:
            QMessageBox.critical(self, "Error inesperado", str(e))
            logging.error(f"Error inesperado login: {e}")
            import traceback
            traceback.print_exc()

    def check_pending_sessions(self, username):
        """Verificar si el usuario tiene sesiones pendientes"""
        try:
            config = self.config_service.load_config()
            if not config:
                return False

            api_config = config.get('api', {})
            api_server = api_config.get('server_ip', '').strip()

            if not api_server:
                logging.warning(
                    "No se puede verificar sesiones: API no configurada")
                return False

            endpoint = f"/usuarios/{username}/sesion_pendiente"
            response = self.api_service.make_request(
                'GET', endpoint, server=api_server)

            if response and response.get('success', False):
                session_data = response.get('data', {})
                pendiente = session_data.get('pendiente', False)

                if pendiente:
                    self.show_pending_session_dialog(session_data, username)
                    return True

            return False

        except Exception as e:
            logging.error(f"Error verificando sesiones: {e}")
            return False

    def show_pending_session_dialog(self, session_data, username):
        """Mostrar diálogo para sesión pendiente usando widget"""
        try:
            dialog = SessionDialogWidget(session_data, username, self)
            dialog.session_close_requested.connect(
                self.handle_close_session_request)
            dialog.exec()

        except Exception as e:
            logging.error(f"Error mostrando diálogo de sesión pendiente: {e}")
            QMessageBox.critical(
                self, "Error", f"Error mostrando información de sesión: {str(e)}")

    def handle_close_session_request(self, session_data, username):
        """Manejar solicitud de cierre de sesión desde el widget"""
        try:
            config = self.config_service.load_config()
            api_config = config.get('api', {})
            api_server = api_config.get('server_ip', '').strip()
            session_id = session_data.get('id_sesion')

            if not session_id:
                QMessageBox.critical(
                    self, "Error", "No se pudo obtener el ID de la sesión")
                return

            endpoint = f"/sesiones/{session_id}/cerrar"
            response = self.api_service.make_request(
                'PUT', endpoint, server=api_server)

            if response and response.get('success', False):
                QMessageBox.information(
                    self, "Sesión Cerrada", "La sesión activa ha sido cerrada correctamente.")

                # ✅ Re-autenticar usuario para continuar (actualizar aquí también)
                username, password = self.login_form_widget.get_credentials()
                auth_result = self.login_service.authenticate_user(
                    username, password)

                if auth_result['success']:  # ✅ Ahora es un dict
                    user_info = auth_result['user_data']
                    self.open_expediente_window(user_info['displayName'])

            else:
                error_msg = response.get(
                    'error', 'Error desconocido') if response else 'No hay respuesta del servidor'
                QMessageBox.critical(
                    self, "Error al Cerrar Sesión", f"No se pudo cerrar la sesión:\n{error_msg}")

        except Exception as e:
            logging.error(f"Error cerrando sesión activa: {e}")
            QMessageBox.critical(
                self, "Error", f"Error inesperado al cerrar sesión:\n{str(e)}")

    # ✅ Agregar username_ldap
    def open_expediente_window(self, user_display_name, username_ldap):
        """Abrir ventana de expedientes"""
        try:
            from gui.expediente_window import ExpedienteWindow

            self.expediente_window = ExpedienteWindow(
                medico_nombre=user_display_name,
                config_service=self.config_service,
                username_ldap=username_ldap  # ✅ Pasar el username LDAP
            )
            self.expediente_window.show()
            self.close()

        except Exception as e:
            logging.error(f"Error abriendo ventana de expedientes: {e}")
            QMessageBox.critical(
                self, "Error", f"Error abriendo expedientes: {str(e)}")

    def closeEvent(self, event):
        """Limpiar recursos al cerrar"""
        try:
            if hasattr(self, 'services_widget'):
                self.services_widget.stop_timer()
            event.accept()
        except Exception as e:
            logging.error(f"Error en closeEvent: {e}")
            event.accept()
