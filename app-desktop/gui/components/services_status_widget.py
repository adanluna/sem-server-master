from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from services.ldap_service import LdapService
from services.api_service import ApiService
import logging
import socket


class ServicesStatusWidget(QWidget):
    def __init__(self, config_service):
        super().__init__()
        self.config_service = config_service
        self.api_service = ApiService()
        self.setup_ui()

        # Timer para verificar servicios periódicamente
        self.service_timer = QTimer()
        self.service_timer.timeout.connect(self.check_all_services)
        self.service_timer.start(30000)  # Verificar cada 30 segundos

        # Verificar servicios inicialmente
        self.check_all_services()

    def setup_ui(self):
        """Configurar la interfaz del widget"""
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Estados de servicios
        self.ldap_status_label = QLabel("🔄 LDAP verificando...")
        self.api_status_label = QLabel("🔄 API verificando...")
        self.rabbit_status_label = QLabel("🔄 RabbitMQ verificando...")

        # Estilo para las etiquetas de estado
        status_style = "font-size: 12px; margin: 2px; padding: 2px;"
        self.ldap_status_label.setStyleSheet(status_style)
        self.api_status_label.setStyleSheet(status_style)
        self.rabbit_status_label.setStyleSheet(status_style)

        self.ldap_status_label.setAlignment(Qt.AlignCenter)
        self.api_status_label.setAlignment(Qt.AlignCenter)
        self.rabbit_status_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.ldap_status_label)
        layout.addWidget(self.api_status_label)
        layout.addWidget(self.rabbit_status_label)

        self.setLayout(layout)

    def check_all_services(self):
        """Verificar el estado de todos los servicios"""
        try:
            self.ldap_ok = self.check_ldap_status()
            self.api_ok = self.check_api_status()
            self.rabbit_ok = self.check_rabbit_status()
        except Exception as e:
            logging.error(f"Error verificando servicios: {e}")
            self.ldap_ok = False
            self.api_ok = False
            self.rabbit_ok = False

    def are_all_services_ok(self):
        """Retornar True si todos los servicios están funcionando"""
        return getattr(self, 'ldap_ok', False) and \
            getattr(self, 'api_ok', False) and \
            getattr(self, 'rabbit_ok', False)

    def check_ldap_status(self):
        """Verificar estado del servidor LDAP y retornar True/False"""
        try:
            config = self.config_service.load_config()
            if not config:
                return False

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
            if not config:
                return False

            api_config = config.get('api', {})
            api_server = api_config.get('server_ip', '').strip()

            if not api_server:
                self.api_status_label.setText("⚠️ API no configurada")
                self.api_status_label.setStyleSheet(
                    "color: #ffc107; font-size: 12px;")
                return False

            # Usar ApiService para verificar estado
            api_status = self.api_service.check_api_status(api_server)

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

                # Si es un 404, probablemente el endpoint /health no existe, pero la API sí
                if '404' in str(error_msg):
                    self.api_status_label.setText("✅ API activa (sin /health)")
                    self.api_status_label.setStyleSheet(
                        "color: #28a745; font-size: 12px;")
                    return True
                else:
                    self.api_status_label.setText(f"⚠️ API con problemas")
                    self.api_status_label.setStyleSheet(
                        "color: #ffc107; font-size: 12px;")
                    return False
            else:
                self.api_status_label.setText("⚠️ API estado desconocido")
                self.api_status_label.setStyleSheet(
                    "color: #ffc107; font-size: 12px;")
                return False

        except Exception as e:
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

    def stop_timer(self):
        """Detener el timer cuando se cierre el widget"""
        if hasattr(self, 'service_timer'):
            self.service_timer.stop()
