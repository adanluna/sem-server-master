import os
import json
import re
import logging
from cryptography.fernet import Fernet, InvalidToken

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ConfigService:
    CONFIG_FILE = 'app-desktop/config.enc'

    def __init__(self, key):
        self.fernet = Fernet(key)

    @staticmethod
    def generate_key():
        """Generar una nueva clave de encriptación"""
        return Fernet.generate_key()

    def save_config(self, config_data):
        json_data = json.dumps(config_data).encode()
        encrypted_data = self.fernet.encrypt(json_data)
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)

            with open(self.CONFIG_FILE, 'wb') as f:
                f.write(encrypted_data)
            logging.info("Configuración guardada correctamente.")
        except Exception as e:
            logging.error(f"Error al guardar configuración: {e}")

    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            logging.warning("Archivo de configuración no encontrado.")
            return None
        try:
            with open(self.CONFIG_FILE, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except InvalidToken:
            logging.error(
                "Archivo de configuración corrupto o clave incorrecta.")
            return None
        except Exception as e:
            logging.error(f"Error al cargar configuración: {e}")
            return None

    @staticmethod
    def is_valid_ip(ip):
        return re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", ip) is not None
