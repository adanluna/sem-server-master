import ldap3
from ldap3 import Server, Connection, ALL, NTLM
from ldap3.core.exceptions import LDAPException
import logging
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(dotenv_path=os.path.join(
    os.path.dirname(__file__), "..", "..", ".env.local"))


class LoginService:
    def __init__(self, config_service=None):
        self.config_service = config_service
        logging.basicConfig(level=logging.INFO)

    def get_ldap_config(self):
        """Obtener configuración LDAP desde config.enc o fallback a .env.local"""
        try:
            if self.config_service:
                config = self.config_service.load_config()
                if config and config.get('ldap_server'):
                    return {
                        'ldap_server': config.get('ldap_server'),
                        'ldap_port': config.get('ldap_port', '389'),
                        'ldap_domain': config.get('ldap_domain', 'semefo.local')
                    }

            # Fallback a variables de entorno si no hay config.enc
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

    def authenticate_user(self, username, password):
        """
        Autentica un usuario contra el servidor LDAP usando configuración desde config.enc

        Args:
            username (str): Nombre de usuario
            password (str): Contraseña

        Returns:
            tuple: (success: bool, user_info: dict, error_message: str)
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
                return True, user_info, ""
            else:
                logging.warning(
                    f"Fallo en autenticación para usuario: {username}")
                return False, {}, "Credenciales incorrectas"

        except LDAPException as e:
            error_msg = f"Error de LDAP: {str(e)}"
            logging.error(error_msg)
            return False, {}, error_msg
        except Exception as e:
            error_msg = f"Error inesperado durante autenticación: {str(e)}"
            logging.error(error_msg)
            return False, {}, error_msg
