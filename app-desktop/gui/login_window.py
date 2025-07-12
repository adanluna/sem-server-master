from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget, QFrame, QDialog
import logging
from ldap3.core.exceptions import LDAPSocketOpenError, LDAPBindError
from services.login_service import LoginService
from services.config_service import ConfigService
from services.utils import load_stylesheet
from services.api_service import ApiService
from services.ldap_service import LdapService
from gui.config_window import ConfigWindow

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ConfigPageWrapper(QWidget):
    """Wrapper para integrar ConfigWindow en el stack con botón de regreso"""

    def __init__(self, config_service, parent_window):
        super().__init__()
        self.config_service = config_service
        self.parent_window = parent_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header con botón de regresar
        header_layout = QHBoxLayout()
        back_button = QPushButton("← Volver al Login")
        back_button.setProperty("class", "settings")
        back_button.clicked.connect(self.parent_window.show_login)
        header_layout.addWidget(back_button)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Crear la página de configuración integrada
        self.config_window = ConfigWindow(
            self.config_service, standalone=False)
        layout.addWidget(self.config_window)


class LoginWindow(QWidget):
    def __init__(self, config_service=None):
        super().__init__()
        self.config_service = config_service
        self.login_service = LoginService(config_service)
        self.api_service = ApiService()
        self.config_wrapper = None

        # Inicializar UI
        self.init_ui()

        # Verificar configuración al inicio
        self.check_configuration_on_startup()

        # Timer para verificar servicios periódicamente
        self.service_timer = QTimer()
        self.service_timer.timeout.connect(self.check_services_status)
        self.service_timer.start(30000)  # Verificar cada 30 segundos

    def init_ui(self):
        # Configuración de la ventana principal
        self.setWindowTitle("SEMEFO - Login")
        self.resize(853, 522)
        self.center_window()

        # Aplicar estilos
        load_stylesheet(self)

        # Crear stacked widget para manejar múltiples páginas
        self.stacked_widget = QStackedWidget()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked_widget)

        # Crear y agregar la página de login
        self.login_page = self.create_login_page()
        self.stacked_widget.addWidget(self.login_page)

        # Mostrar la página de login inicialmente
        self.stacked_widget.setCurrentIndex(0)

    def center_window(self):
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def create_login_page(self):
        page = QWidget()

        # Configuración del botón de configuración (esquina superior derecha)
        self.button_config = QPushButton("⚙")
        self.button_config.setProperty("class", "settings")
        self.button_config.setFixedSize(50, 50)
        self.button_config.setToolTip("Configuración")
        self.button_config.clicked.connect(self.show_config)

        # Logo más pequeño
        self.label_logo = QLabel("Logotipo")
        logo_pixmap = QPixmap(u"logo.png")
        if not logo_pixmap.isNull():
            # Redimensionar el logo a un tamaño más pequeño
            scaled_pixmap = logo_pixmap.scaled(
                80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label_logo.setPixmap(scaled_pixmap)
        self.label_logo.setAlignment(Qt.AlignCenter)

        # Campos de login
        self.label_user = QLabel("Usuario:")
        self.input_user = QLineEdit()
        self.input_user.setText("forense1")
        self.input_user.setFixedWidth(250)

        self.label_pass = QLabel("Contraseña:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.setText("Pi$to01")
        self.input_pass.setFixedWidth(250)

        self.button_login = QPushButton("Iniciar Sesión")
        self.button_login.setProperty("class", "action-button")
        self.button_login.setFixedWidth(250)
        self.button_login.clicked.connect(self.login)

        # Solo 3 estados de servicios
        self.ldap_status_label = QLabel("🔄 LDAP verificando...")
        self.api_status_label = QLabel("🔄 API verificando...")
        self.rabbit_status_label = QLabel("🔄 RabbitMQ verificando...")

        # Estilo simple para las etiquetas de estado
        status_style = "font-size: 12px; margin: 2px; padding: 2px;"
        self.ldap_status_label.setStyleSheet(status_style)
        self.api_status_label.setStyleSheet(status_style)
        self.rabbit_status_label.setStyleSheet(status_style)

        self.ldap_status_label.setAlignment(Qt.AlignCenter)
        self.api_status_label.setAlignment(Qt.AlignCenter)
        self.rabbit_status_label.setAlignment(Qt.AlignCenter)

        # Layout principal centrado
        main_layout = QVBoxLayout()

        # Header con botón de configuración
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        header_layout.addWidget(self.button_config)

        # Contenido centrado
        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignCenter)
        content_layout.setSpacing(20)

        # Formulario de login
        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(15)
        form_layout.addWidget(self.label_logo)
        form_layout.addWidget(self.label_user)
        form_layout.addWidget(self.input_user)
        form_layout.addWidget(self.label_pass)
        form_layout.addWidget(self.input_pass)
        form_layout.addWidget(self.button_login)

        # Solo agregar los 3 servicios, sin config_status_label ni db_status_label
        form_layout.addWidget(self.ldap_status_label)
        form_layout.addWidget(self.api_status_label)
        form_layout.addWidget(self.rabbit_status_label)

        content_layout.addLayout(form_layout)

        main_layout.addLayout(header_layout)
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addStretch()

        page.setLayout(main_layout)
        return page

    def show_config(self):
        """Mostrar ventana de configuración"""
        try:
            if self.config_service is None:
                QMessageBox.warning(
                    self, "Error", "Servicio de configuración no disponible")
                return

            # Si es la primera vez, crear el wrapper de configuración
            if self.stacked_widget.count() == 1:
                self.config_wrapper = ConfigPageWrapper(
                    self.config_service, self)
                self.stacked_widget.addWidget(self.config_wrapper)

            # Cambiar a la página de configuración
            self.stacked_widget.setCurrentIndex(1)
            logging.info("Mostrando configuración integrada en login")

        except Exception as e:
            logging.error(f"Error mostrando configuración: {e}")
            QMessageBox.critical(
                self, "Error", f"Error al mostrar configuración: {str(e)}")

    def show_login(self):
        """Volver a la página de login desde configuración"""
        self.stacked_widget.setCurrentIndex(0)
        # Re-verificar configuración y servicios al volver del config
        self.check_configuration_on_startup()
        logging.info("Regresando a página de login")

    def check_configuration_on_startup(self):
        try:
            if not self.config_service:
                self.show_config_warning(
                    "Servicio de configuración no disponible")
                return

            config = self.config_service.load_config()
            if not config:
                self.show_config_warning("Archivo config.json no encontrado")
                return

            # Validar configuración completa
            validation_errors = self.validate_complete_configuration(config)
            if validation_errors:
                self.show_config_warning(
                    f"Configuración incompleta: {', '.join(validation_errors)}")
                return

            # Si la configuración está completa, verificar servicios
            self.check_services_status()

        except Exception as e:
            logging.error(f"Error verificando configuración: {e}")
            self.show_config_warning("Error al verificar configuración")

    def validate_complete_configuration(self, config):
        """Validar que todas las configuraciones requeridas estén presentes"""
        errors = []

        # Validar LDAP
        ldap_config = config.get('ldap', {})
        if not ldap_config.get('server', '').strip():
            errors.append("servidor LDAP")
        if not ldap_config.get('domain', '').strip():
            errors.append("dominio LDAP")
        if not ldap_config.get('port', '').strip():
            errors.append("puerto LDAP")

        # Validar API
        api_config = config.get('api', {})
        if not api_config.get('server_ip', '').strip():
            errors.append("servidor API")

        # Validar Dispositivo
        dispositivo_config = config.get('dispositivo', {})
        if not dispositivo_config.get('tablet_id', '').strip():
            errors.append("ID de tablet")
        if not dispositivo_config.get('plancha', '').strip():
            errors.append("plancha")

        # Validar Cámaras
        camaras_config = config.get('camaras', {})
        if not camaras_config.get('camera1_ip', '').strip():
            errors.append("IP cámara 1")
        if not camaras_config.get('camera2_ip', '').strip():
            errors.append("IP cámara 2")

        return errors

    def check_services_status(self):
        """Verificar el estado de los servicios y habilitar/deshabilitar login"""
        try:
            # Verificar los 3 servicios
            ldap_ok = self.check_ldap_status()
            api_ok = self.check_api_status()
            rabbit_ok = self.check_rabbit_status()

            # Solo habilitar login si TODOS los servicios están funcionando
            if ldap_ok and api_ok and rabbit_ok:
                self.enable_login()
            else:
                self.disable_login_services()

        except Exception as e:
            logging.error(f"Error verificando servicios: {e}")
            self.disable_login_services()

    def check_ldap_status(self):
        """Verificar estado del servidor LDAP y retornar True/False"""
        try:
            config = self.config_service.load_config()
            ldap_config = config.get('ldap', {})
            ldap_server = ldap_config.get('server', '').strip()
            ldap_port = int(ldap_config.get('port', 389))
            ldap_domain = ldap_config.get('domain', '').strip()

            if not ldap_server:
                self.ldap_status_label.setText("⚠️ LDAP no configurado")
                self.ldap_status_label.setStyleSheet(
                    "color: #ffc107; font-size: 12px;")
                return False

            # Usar LdapService para verificar conectividad
            ldap_service = LdapService(ldap_server, ldap_port, ldap_domain)
            if ldap_service.test_connection():
                self.ldap_status_label.setText("✅ LDAP activo")
                self.ldap_status_label.setStyleSheet(
                    "color: #28a745; font-size: 12px;")
                return True
            else:
                self.ldap_status_label.setText("❌ LDAP desconectado")
                self.ldap_status_label.setStyleSheet(
                    "color: #dc3545; font-size: 12px;")
                return False

        except Exception as e:
            self.ldap_status_label.setText("❌ LDAP error de conexión")
            self.ldap_status_label.setStyleSheet(
                "color: #dc3545; font-size: 12px;")
            logging.error(f"Error verificando LDAP: {e}")
            return False

    def check_api_status(self):
        """Verificar estado de la API y retornar True/False"""
        try:
            config = self.config_service.load_config()
            api_config = config.get('api', {})
            api_server = api_config.get('server_ip', '').strip()

            print(f"🔍 DEBUG API Status: Server configurado: '{api_server}'")

            if not api_server:
                self.api_status_label.setText("⚠️ API no configurada")
                self.api_status_label.setStyleSheet(
                    "color: #ffc107; font-size: 12px;")
                return False

            # Usar ApiService para verificar estado
            print("🔍 DEBUG API Status: Llamando check_api_status...")
            api_status = self.api_service.check_api_status(api_server)

            print(f"🔍 DEBUG API Status: Resultado: {api_status}")

            if api_status['status'] == 'online':
                response_time = api_status.get('response_time', 0)
                self.api_status_label.setText(
                    f"✅ API activa ({response_time}ms)")
                self.api_status_label.setStyleSheet(
                    "color: #28a745; font-size: 12px;")
                return True
            elif api_status['status'] == 'offline':
                self.api_status_label.setText("❌ API desconectada")
                self.api_status_label.setStyleSheet(
                    "color: #dc3545; font-size: 12px;")
                return False
            elif api_status['status'] == 'error':
                error_msg = api_status.get('error', 'Error desconocido')
                print(f"🔍 DEBUG API Status: Error específico: {error_msg}")

                # Si es un 404, probablemente el endpoint /health no existe, pero la API sí
                if '404' in str(error_msg):
                    print(
                        "🔍 DEBUG API Status: 404 en /health, pero API está respondiendo")
                    self.api_status_label.setText("✅ API activa (sin /health)")
                    self.api_status_label.setStyleSheet(
                        "color: #28a745; font-size: 12px;")
                    return True
                else:
                    self.api_status_label.setText(
                        f"⚠️ API con problemas ({error_msg})")
                    self.api_status_label.setStyleSheet(
                        "color: #ffc107; font-size: 12px;")
                    return False
            else:
                print(
                    f"🔍 DEBUG API Status: Estado desconocido: {api_status['status']}")
                self.api_status_label.setText("⚠️ API estado desconocido")
                self.api_status_label.setStyleSheet(
                    "color: #ffc107; font-size: 12px;")
                return False

        except Exception as e:
            print(f"🔍 DEBUG API Status: Excepción: {e}")
            self.api_status_label.setText("❌ API error de conexión")
            self.api_status_label.setStyleSheet(
                "color: #dc3545; font-size: 12px;")
            logging.error(f"Error verificando API: {e}")
            return False

    def check_rabbit_status(self):
        """Verificar estado del servidor RabbitMQ y retornar True/False"""
        try:
            # RabbitMQ se configura desde .env, no desde config.json
            rabbit_host = "localhost"
            rabbit_port = 5672  # Puerto AMQP mapeado en docker-compose

            # Verificar conectividad básica con socket
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((rabbit_host, rabbit_port))
            sock.close()

            if result == 0:
                self.rabbit_status_label.setText("✅ RabbitMQ activo")
                self.rabbit_status_label.setStyleSheet(
                    "color: #28a745; font-size: 12px;")
                return True
            else:
                self.rabbit_status_label.setText("❌ RabbitMQ desconectado")
                self.rabbit_status_label.setStyleSheet(
                    "color: #dc3545; font-size: 12px;")
                return False

        except Exception as e:
            self.rabbit_status_label.setText("❌ RabbitMQ error de conexión")
            self.rabbit_status_label.setStyleSheet(
                "color: #dc3545; font-size: 12px;")
            logging.error(f"Error verificando RabbitMQ: {e}")
            return False

    def show_config_warning(self, message):
        """Mostrar advertencia de configuración y deshabilitar login"""
        self.button_login.setEnabled(False)
        self.button_login.setStyleSheet(
            "background-color: #cccccc; color: #666666;")
        self.button_login.setText("Configurar primero")
        self.button_login.setToolTip(f"Completar configuración: {message}")
        logging.warning(f"Configuración requerida: {message}")

    def disable_login_services(self):
        """Deshabilitar login por servicios no disponibles"""
        self.button_login.setEnabled(False)
        self.button_login.setStyleSheet(
            "background-color: #cccccc; color: #666666;")
        self.button_login.setText("Servicios no disponibles")
        self.button_login.setToolTip(
            "Todos los servicios (LDAP, API, RabbitMQ) deben estar activos")
        logging.warning("Login deshabilitado: servicios no disponibles")

    def enable_login(self):
        """Habilitar login cuando todo está correcto"""
        self.button_login.setEnabled(True)
        self.button_login.setStyleSheet("")
        self.button_login.setText("Iniciar Sesión")
        self.button_login.setToolTip("")
        logging.info("Login habilitado: configuración y servicios OK")

    def login(self):
        print("🔍 DEBUG: Entrando a función login()")

        if not self.button_login.isEnabled():
            print("🔍 DEBUG: Botón de login deshabilitado")
            # Mostrar mensaje específico según el estado
            if self.button_login.text() == "Configurar primero":
                QMessageBox.warning(
                    self, "Configuración incompleta",
                    "Debe completar la configuración antes de iniciar sesión.\n\n"
                    "Haga clic en el botón ⚙ para configurar todos los parámetros requeridos."
                )
            else:
                QMessageBox.warning(
                    self, "Servicios no disponibles",
                    "Todos los servicios (LDAP, API, RabbitMQ) deben estar activos para iniciar sesión.\n\n"
                    "Verifique que Docker esté ejecutándose y todos los servicios estén funcionando."
                )
            return

        username = self.input_user.text()
        password = self.input_pass.text()
        print(
            f"🔍 DEBUG: Usuario: '{username}', Password: {'*' * len(password) if password else 'VACÍO'}")

        if not username or not password:
            print("🔍 DEBUG: Campos vacíos")
            QMessageBox.warning(self, "Campos requeridos",
                                "Por favor ingrese usuario y contraseña.")
            return

        try:
            print("🔍 DEBUG: Iniciando autenticación LDAP...")
            # 1. Autenticar usuario con LDAP
            success, user_info, error_message = self.login_service.authenticate_user(
                username, password)

            print(f"🔍 DEBUG: Resultado LDAP - Success: {success}")
            if user_info:
                print(f"🔍 DEBUG: User info: {user_info}")
            if error_message:
                print(f"🔍 DEBUG: Error message: {error_message}")

            if not success:
                print("🔍 DEBUG: Autenticación LDAP falló")
                QMessageBox.critical(
                    self, "Error de Autenticación", error_message)
                logging.warning(f"Usuario {username} falló autenticación.")
                return

            print(
                "🔍 DEBUG: Autenticación LDAP exitosa, verificando sesiones pendientes...")
            logging.info(f"Usuario {username} autenticado correctamente.")

            # 2. Verificar si tiene sesiones pendientes
            print(f"🔍 DEBUG: Llamando check_pending_sessions('{username}')")
            if self.check_pending_sessions(username):
                print("🔍 DEBUG: Sesión pendiente encontrada, deteniendo login")
                return  # Si hay sesión pendiente, no continuar con el login

            print("🔍 DEBUG: No hay sesiones pendientes, abriendo expedientes")
            # 3. Si no hay sesiones pendientes, continuar al expediente
            self.open_expediente_window(user_info['displayName'])

        except (LDAPSocketOpenError, LDAPBindError) as e:
            print(f"🔍 DEBUG: Error LDAP: {e}")
            QMessageBox.critical(self, "LDAP Error", str(e))
            logging.error(f"LDAP Error: {e}")
        except Exception as e:
            print(f"🔍 DEBUG: Error inesperado: {e}")
            QMessageBox.critical(self, "Error inesperado", str(e))
            logging.error(f"Error inesperado login: {e}")

    def check_pending_sessions(self, username):
        """Verificar si el usuario tiene sesiones pendientes usando ApiService"""
        print(
            f"🔍 DEBUG: check_pending_sessions() - Entrada con username: '{username}'")

        try:
            print("🔍 DEBUG: Cargando configuración...")
            config = self.config_service.load_config()

            if not config:
                print("🔍 DEBUG: No se pudo cargar configuración")
                return False

            print(f"🔍 DEBUG: Configuración cargada: {config}")

            api_config = config.get('api', {})
            api_server = api_config.get('server_ip', '').strip()

            print(f"🔍 DEBUG: API config: {api_config}")
            print(f"🔍 DEBUG: API server: '{api_server}'")

            if not api_server:
                print("🔍 DEBUG: API server no configurado")
                logging.warning(
                    "No se puede verificar sesiones: API no configurada")
                return False

            # Usar ApiService para verificar sesiones pendientes
            endpoint = f"/usuarios/{username}/sesion_pendiente"
            print(f"🔍 DEBUG: Endpoint a llamar: '{endpoint}'")
            print(f"🔍 DEBUG: Server completo: '{api_server}'")

            print("🔍 DEBUG: Llamando a api_service.make_request()...")
            response = self.api_service.make_request(
                'GET', endpoint, server=api_server)

            print(f"🔍 DEBUG: Respuesta cruda del API: {response}")
            print(f"🔍 DEBUG: Tipo de respuesta: {type(response)}")

            if response and response.get('success', False):
                print("🔍 DEBUG: Respuesta exitosa del API")
                session_data = response.get('data', {})
                print(f"🔍 DEBUG: Session data: {session_data}")

                pendiente = session_data.get('pendiente', False)
                print(f"🔍 DEBUG: ¿Sesión pendiente?: {pendiente}")

                if pendiente:
                    print("🔍 DEBUG: Sesión pendiente encontrada, mostrando diálogo")
                    # Mostrar diálogo de sesión pendiente
                    self.show_pending_session_dialog(session_data, username)
                    return True
                else:
                    print("🔍 DEBUG: No hay sesiones pendientes")
                    return False
            else:
                print("🔍 DEBUG: Respuesta del API no exitosa o vacía")
                error_msg = response.get(
                    'error', 'Error desconocido') if response else 'No hay respuesta'
                print(f"🔍 DEBUG: Error message: {error_msg}")
                logging.warning(f"Error verificando sesiones: {error_msg}")
                return False

        except Exception as e:
            print(f"🔍 DEBUG: Excepción en check_pending_sessions: {e}")
            import traceback
            traceback.print_exc()
            logging.error(f"Error inesperado verificando sesiones: {e}")
            return False

    def show_pending_session_dialog(self, session_data, username):
        """Mostrar diálogo para sesión pendiente encontrada"""
        print(f"🔍 DEBUG: show_pending_session_dialog() - Entrada")
        print(f"🔍 DEBUG: Session data recibida: {session_data}")
        print(f"🔍 DEBUG: Username: '{username}'")

        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Sesión Activa Encontrada")
            dialog.setModal(True)
            dialog.resize(450, 300)

            layout = QVBoxLayout()

            # Título
            title_label = QLabel("⚠️ Sesión Activa Detectada")
            title_label.setStyleSheet(
                "font-weight: bold; font-size: 16px; color: #ff6b35; margin-bottom: 10px;")
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)

            # Información de la sesión
            expediente = session_data.get('numero_expediente', 'N/A')
            nombre_sesion = session_data.get('nombre_sesion', 'N/A')
            plancha = session_data.get('plancha', 'N/A')
            tablet = session_data.get('tablet', 'N/A')

            print(f"🔍 DEBUG: Expediente: '{expediente}'")
            print(f"🔍 DEBUG: Nombre sesión: '{nombre_sesion}'")
            print(f"🔍 DEBUG: Plancha: '{plancha}'")
            print(f"🔍 DEBUG: Tablet: '{tablet}'")

            info_text = f"""
El usuario '{username}' tiene una sesión activa en curso:

📁 Expediente: {expediente}
🎯 Sesión: {nombre_sesion}
🏥 Plancha: {plancha}
📱 Tablet: {tablet}

Debe cerrar la sesión activa antes de continuar.
"""

            info_label = QLabel(info_text)
            info_label.setStyleSheet(
                "font-size: 12px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)

            # Botones
            button_layout = QHBoxLayout()

            close_session_button = QPushButton("🚪 Cerrar Sesión Activa")
            close_session_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            close_session_button.clicked.connect(
                lambda: self.close_active_session(
                    session_data, username, dialog)
            )

            cancel_button = QPushButton("❌ Cancelar Login")
            cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
            cancel_button.clicked.connect(dialog.reject)

            button_layout.addWidget(close_session_button)
            button_layout.addWidget(cancel_button)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)

            print("🔍 DEBUG: Mostrando diálogo...")
            # Centrar el diálogo
            dialog.exec()

        except Exception as e:
            print(f"🔍 DEBUG: Error en show_pending_session_dialog: {e}")
            import traceback
            traceback.print_exc()
            logging.error(f"Error mostrando diálogo de sesión pendiente: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Error mostrando información de sesión: {str(e)}"
            )

    def close_active_session(self, session_data, username, dialog):
        """Cerrar la sesión activa usando ApiService"""
        print(f"🔍 DEBUG: close_active_session() - Entrada")
        print(f"🔍 DEBUG: Session data: {session_data}")
        print(f"🔍 DEBUG: Username: '{username}'")

        try:
            config = self.config_service.load_config()
            api_config = config.get('api', {})
            api_server = api_config.get('server_ip', '').strip()

            session_id = session_data.get('id_sesion')
            print(f"🔍 DEBUG: Session ID: {session_id}")
            print(f"🔍 DEBUG: API Server: '{api_server}'")

            if not session_id:
                print("🔍 DEBUG: No se encontró session_id")
                QMessageBox.critical(
                    dialog, "Error",
                    "No se pudo obtener el ID de la sesión"
                )
                return

            # Usar ApiService para cerrar la sesión
            endpoint = f"/sesiones/{session_id}/cerrar"
            print(f"🔍 DEBUG: Endpoint para cerrar: '{endpoint}'")

            print("🔍 DEBUG: Llamando API para cerrar sesión...")
            response = self.api_service.make_request(
                'PUT', endpoint, server=api_server)

            print(f"🔍 DEBUG: Respuesta del cierre: {response}")

            if response and response.get('success', False):
                print("🔍 DEBUG: Sesión cerrada exitosamente")
                dialog.accept()
                QMessageBox.information(
                    self, "Sesión Cerrada",
                    f"La sesión activa ha sido cerrada correctamente.\n\n"
                    f"Ahora puede continuar con el login."
                )

                print("🔍 DEBUG: Re-autenticando usuario para continuar...")
                # Obtener info del usuario nuevamente para continuar
                success, user_info, _ = self.login_service.authenticate_user(
                    self.input_user.text(), self.input_pass.text()
                )

                if success:
                    print("🔍 DEBUG: Re-autenticación exitosa, abriendo expedientes")
                    self.open_expediente_window(user_info['displayName'])
                else:
                    print("🔍 DEBUG: Fallo en re-autenticación")

            else:
                print("🔍 DEBUG: Error cerrando sesión")
                error_msg = response.get(
                    'error', 'Error desconocido') if response else 'No hay respuesta del servidor'

                print(f"🔍 DEBUG: Error msg: {error_msg}")
                QMessageBox.critical(
                    dialog, "Error al Cerrar Sesión",
                    f"No se pudo cerrar la sesión:\n{error_msg}"
                )

        except Exception as e:
            print(f"🔍 DEBUG: Excepción en close_active_session: {e}")
            import traceback
            traceback.print_exc()
            logging.error(f"Error cerrando sesión activa: {e}")
            QMessageBox.critical(
                dialog, "Error",
                f"Error inesperado al cerrar sesión:\n{str(e)}"
            )

    def open_expediente_window(self, medico_nombre):
        """Abrir ventana de expedientes"""
        try:
            from .expediente_window import ExpedienteWindow
            self.expediente_window = ExpedienteWindow(
                medico_nombre=medico_nombre,
                config_service=self.config_service
            )
            self.expediente_window.show()
            self.close()
        except Exception as e:
            logging.error(f"Error abriendo ventana expediente: {e}")
            QMessageBox.critical(
                self, "Error", f"Error al abrir expedientes: {str(e)}")

    def closeEvent(self, event):
        """Limpiar recursos al cerrar"""
        try:
            if hasattr(self, 'service_timer'):
                self.service_timer.stop()
            event.accept()
        except Exception as e:
            logging.error(f"Error en closeEvent: {e}")
            event.accept()
