import ldap3
from ldap3 import Server, Connection, ALL, NTLM
from ldap3.core.exceptions import LDAPException
import logging
import os
from dotenv import load_dotenv
from .api_service import ApiService

# Cargar variables de entorno - CAMBIAR A .env
load_dotenv(dotenv_path=os.path.join(
    os.path.dirname(__file__), "..", "..", ".env"))


class LoginService:
    def __init__(self, config_service=None):
        self.config_service = config_service
        self.api_service = ApiService()
        logging.basicConfig(level=logging.INFO)

    def get_ldap_config(self):
        """Obtener configuración LDAP desde config.enc o fallback a .env"""
        try:
            if self.config_service:
                config = self.config_service.load_config()
                if config and config.get('ldap_server'):
                    return {
                        'ldap_server': config.get('ldap_server'),
                        'ldap_port': config.get('ldap_port', '389'),
                        'ldap_domain': config.get('ldap_domain', 'semefo.local')
                    }

            # Fallback a variables de entorno del archivo .env
            return {
                'ldap_server': os.getenv('LDAP_SERVER_IP', '192.168.1.211'),
                'ldap_port': os.getenv('LDAP_PORT', '389'),
                'ldap_domain': os.getenv('LDAP_DOMAIN', 'semefo.local')
            }

        except Exception as e:
            logging.error(f"Error obteniendo configuración LDAP: {e}")
            # Fallback a valores por defecto
            return {
                'ldap_server': '192.168.1.211',
                'ldap_port': '389',
                'ldap_domain': 'semefo.local'
            }

    def check_pending_session(self, username):
        """
        Verificar si el usuario tiene sesiones pendientes

        Args:
            username (str): Nombre de usuario

        Returns:
            dict: Datos de la sesión pendiente si existe, None si no hay sesiones
        """
        print(
            f"🔍 DEBUG LoginService.check_pending_session: Verificando para usuario: {username}")

        try:
            # Obtener configuración del servidor API
            if self.config_service:
                config = self.config_service.load_config()
                api_server = config.get('api_server', 'localhost:8000')
            else:
                api_server = 'localhost:8000'

            print(
                f"🔍 DEBUG LoginService.check_pending_session: Usando servidor API: {api_server}")

            # Hacer petición al endpoint de sesión pendiente
            endpoint = f"/usuarios/{username}/sesion_pendiente"
            response = self.api_service.get(endpoint, server=api_server)

            print(
                f"🔍 DEBUG LoginService.check_pending_session: Respuesta del API: {response}")

            if response.get('success'):
                session_data = response.get('data', {})
                print(
                    f"🔍 DEBUG LoginService.check_pending_session: Datos de sesión: {session_data}")

                # Si hay sesión pendiente, devolver los datos
                if session_data.get('pendiente', False):
                    print(
                        "🔍 DEBUG LoginService.check_pending_session: Sesión pendiente encontrada")
                    return session_data
                else:
                    print(
                        "🔍 DEBUG LoginService.check_pending_session: No hay sesiones pendientes")
                    return None
            else:
                print(
                    f"🔍 DEBUG LoginService.check_pending_session: Error en API: {response.get('error')}")
                return None

        except Exception as e:
            print(
                f"🔍 DEBUG LoginService.check_pending_session: Excepción: {e}")
            import traceback
            traceback.print_exc()
            return None

    def authenticate_user(self, username, password):
        """
        Autentica un usuario contra el servidor LDAP usando configuración desde config.enc

        Args:
            username (str): Nombre de usuario
            password (str): Contraseña

        Returns:
            dict: {'success': bool, 'user_data': dict, 'error': str}
        """
        try:
            # Obtener configuración LDAP
            ldap_config = self.get_ldap_config()

            server_ip = ldap_config['ldap_server']
            server_port = int(ldap_config['ldap_port'])
            domain = ldap_config['ldap_domain']

            logging.info(
                f"Intentando autenticación LDAP con servidor: {server_ip}:{server_port} (dominio: {domain})")

            # Crear servidor LDAP
            server = Server(server_ip, port=server_port, get_info=ALL)

            # Formatear username con dominio
            user_dn = f"{username}@{domain}"

            # Crear conexión
            conn = Connection(server, user=user_dn,
                              password=password, auto_bind=True)

            if conn.bind():
                # Buscar información del usuario
                search_base = f"DC={domain.split('.')[0]},DC={domain.split('.')[1]}"
                search_filter = f"(sAMAccountName={username})"

                conn.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    attributes=['displayName', 'mail', 'department', 'title']
                )

                user_info = {
                    'username': username,
                    'displayName': username,  # Valor por defecto
                    'mail': '',
                    'department': '',
                    'title': ''
                }

                if conn.entries:
                    entry = conn.entries[0]
                    user_info.update({
                        'displayName': str(entry.displayName) if entry.displayName else username,
                        'mail': str(entry.mail) if entry.mail else '',
                        'department': str(entry.department) if entry.department else '',
                        'title': str(entry.title) if entry.title else ''
                    })

                conn.unbind()
                logging.info(f"Autenticación exitosa para usuario: {username}")
                return {
                    'success': True,
                    'user_data': user_info,
                    'error': ''
                }
            else:
                logging.warning(
                    f"Fallo en autenticación para usuario: {username}")
                return {
                    'success': False,
                    'user_data': {},
                    'error': 'Credenciales incorrectas'
                }

        except LDAPException as e:
            error_msg = f"Error de LDAP: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'user_data': {},
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado durante autenticación: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'user_data': {},
                'error': error_msg
            }
