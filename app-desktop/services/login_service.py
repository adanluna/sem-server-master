from ldap3 import Server, Connection, ALL, core
import logging
import os
from dotenv import load_dotenv

load_dotenv()


class LoginService:
    def __init__(self):
        self.ldap_server_ip = os.getenv("LDAP_SERVER_IP")
        self.ldap_port = int(os.getenv("LDAP_PORT"))
        self.domain = os.getenv("LDAP_DOMAIN")
        self.base_dn = self._get_base_dn()

    def _get_base_dn(self):
        parts = self.domain.split(".")
        return ",".join([f"dc={part}" for part in parts])

    def authenticate_user(self, username, password):
        user_bind = f"{username}@{self.domain}"

        try:
            server = Server(self.ldap_server_ip,
                            port=self.ldap_port, get_info=ALL)
            conn = Connection(server, user=user_bind,
                              password=password, auto_bind=True)

            logging.info(f"✅ Usuario autenticado correctamente: {username}")

            conn.search(self.base_dn,
                        f'(sAMAccountName={username})',
                        attributes=['displayName', 'mail', 'memberOf'])

            user_data = {}
            for entry in conn.entries:
                user_data['displayName'] = entry.displayName.value
                user_data['email'] = entry.mail.value
                user_data['groups'] = entry.memberOf

            conn.unbind()
            return True, user_data, None

        except core.exceptions.LDAPBindError as e:
            error_msg = f"Credenciales inválidas para usuario '{username}'"
            logging.warning(
                f"❌ Fallo de autenticación para usuario: {username}")
            return False, None, error_msg
        except core.exceptions.LDAPSocketOpenError as e:
            error_msg = f"No se puede conectar al servidor LDAP ({self.ldap_server_ip}:{self.ldap_port}). Verifique la conexión de red."
            logging.error(f"❌ Error de socket LDAP: {str(e)}")
            return False, None, error_msg
        except Exception as ex:
            error_msg = f"Error de conexión: {str(ex)}"
            logging.error(f"❌ Error general: {str(ex)}")
            return False, None, error_msg
