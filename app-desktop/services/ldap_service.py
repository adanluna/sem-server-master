from ldap3 import Server, Connection, ALL, core
import logging
from typing import Optional, Dict, Any


class LdapService:
    def __init__(self, server_ip: str, port: int = 389, domain: str = ""):
        """
        Servicio para autenticación LDAP/Active Directory

        Args:
            server_ip: IP del servidor LDAP
            port: Puerto LDAP (389 por defecto)
            domain: Dominio (ej: semefo.local)
        """
        self.server_ip = server_ip
        self.port = port
        self.domain = domain

        # Calcular base DN
        try:
            if domain:
                parts = domain.split(".")
                self.base_dn = ",".join([f"dc={part}" for part in parts])
            else:
                self.base_dn = ""
        except Exception as e:
            logging.error(f"Error procesando dominio LDAP: {e}")
            self.base_dn = ""

    def authenticate(self, username: str, password: str) -> bool:
        """
        Autenticar usuario contra LDAP/Active Directory

        Args:
            username: Nombre de usuario (sin @domain)
            password: Contraseña

        Returns:
            True si la autenticación es exitosa, False en caso contrario
        """
        try:
            # Formar el user bind
            if self.domain:
                user_bind = f"{username}@{self.domain}"
            else:
                user_bind = username

            logging.info(
                f"🔍 Intentando autenticar: {user_bind} en {self.server_ip}:{self.port}")

            # Crear conexión al servidor LDAP
            server = Server(self.server_ip, port=self.port, get_info=ALL)
            conn = Connection(server, user=user_bind,
                              password=password, auto_bind=True)

            logging.info(f"✅ Autenticación exitosa para: {username}")

            # Cerrar conexión
            conn.unbind()
            return True

        except core.exceptions.LDAPBindError as e:
            logging.warning(f"❌ Credenciales inválidas para {username}: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Error de conexión LDAP para {username}: {e}")
            return False

    def get_user_info(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información del usuario autenticado

        Returns:
            Diccionario con información del usuario o None si falla
        """
        try:
            if self.domain:
                user_bind = f"{username}@{self.domain}"
            else:
                user_bind = username

            server = Server(self.server_ip, port=self.port, get_info=ALL)
            conn = Connection(server, user=user_bind,
                              password=password, auto_bind=True)

            # Buscar información del usuario
            if self.base_dn:
                conn.search(self.base_dn,
                            f'(sAMAccountName={username})',
                            attributes=['displayName', 'mail', 'memberOf'])

                if conn.entries:
                    entry = conn.entries[0]
                    user_info = {
                        'username': username,
                        'display_name': entry.displayName.value if entry.displayName else username,
                        'email': entry.mail.value if entry.mail else '',
                        'groups': [str(group) for group in entry.memberOf] if entry.memberOf else []
                    }

                    conn.unbind()
                    return user_info

            conn.unbind()
            return {
                'username': username,
                'display_name': username,
                'email': '',
                'groups': []
            }

        except Exception as e:
            logging.error(
                f"Error obteniendo información del usuario {username}: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Probar conectividad básica con el servidor LDAP

        Returns:
            True si se puede conectar al servidor, False en caso contrario
        """
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.server_ip, self.port))
            sock.close()

            if result == 0:
                logging.info(
                    f"✅ Conectividad LDAP OK: {self.server_ip}:{self.port}")
                return True
            else:
                logging.warning(
                    f"❌ No se puede conectar a LDAP: {self.server_ip}:{self.port}")
                return False

        except Exception as e:
            logging.error(f"❌ Error probando conexión LDAP: {e}")
            return False

    def authenticate_user(self, username, password):
        try:
            # Cargar configuración LDAP
            config = self.config_service.load_config()
            if not config:
                raise Exception("No se pudo cargar la configuración")

            ldap_config = config.get('ldap', {})
            ldap_server = ldap_config.get('server', '')
            ldap_domain = ldap_config.get('domain', '')
            ldap_port = int(ldap_config.get('port', 389))

            if not ldap_server or not ldap_domain:
                raise Exception("Configuración LDAP incompleta")

            # 🚀 Crear LdapService con los parámetros correctos
            ldap_service = LdapService(
                server_ip=ldap_server,
                port=ldap_port,
                domain=ldap_domain
            )

            # 🚀 Usar el método authenticate() del LdapService
            auth_success = ldap_service.authenticate(username, password)

            if auth_success:
                # Obtener información del usuario
                user_info = ldap_service.get_user_info(username, password)

                if user_info:
                    logging.info(
                        f"Usuario {username} autenticado exitosamente")
                    return True, user_info
                else:
                    # Autenticación exitosa pero sin info adicional
                    basic_info = {
                        'username': username,
                        'display_name': username,
                        'email': '',
                        'groups': []
                    }
                    logging.info(
                        f"Usuario {username} autenticado (info básica)")
                    return True, basic_info
            else:
                logging.warning(f"Fallo de autenticación para {username}")
                return False, "Credenciales inválidas"

        except Exception as e:
            logging.error(f"Error en autenticación: {e}")
            return False, f"Error de autenticación: {str(e)}"

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
            # Usar el método authenticate_user de la clase
            success, user_info_or_error = self.authenticate_user(
                username, password)

            if success:
                logging.info(f"Usuario {username} autenticado correctamente.")

                # Verificar sesiones pendientes
                if self.check_user_pending_session(username):
                    return

                # 🚀 Obtener el nombre del usuario usando el campo correcto
                display_name = user_info_or_error.get('display_name', username) if isinstance(
                    user_info_or_error, dict) else username
                self.open_expediente_window(display_name)
            else:
                QMessageBox.critical(
                    self, "Error de Autenticación", user_info_or_error)
                logging.warning(f"Usuario {username} falló autenticación.")

        except Exception as e:
            QMessageBox.critical(self, "Error inesperado", str(e))
            logging.error(f"Error inesperado login: {e}")

    def check_ldap_connectivity(self, ldap_server: str, port: int = 389) -> bool:
        """Verificar conectividad básica con el servidor LDAP"""
        try:
            # Usar el método del LdapService si está disponible
            config = self.config_service.load_config()
            if config:
                ldap_config = config.get('ldap', {})
                ldap_domain = ldap_config.get('domain', '')

                # Crear una instancia temporal de LdapService
                temp_ldap_service = LdapService(
                    server_ip=ldap_server, port=port, domain=ldap_domain)

                # Probar la conexión
                return temp_ldap_service.test_connection()

            return False

        except Exception as e:
            logging.error(f"Error verificando conectividad LDAP: {e}")
            return False
