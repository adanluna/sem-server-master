import os
import json
from cryptography.fernet import Fernet

class ConfigService:
    CONFIG_FILE = 'app-desktop/config.enc'

    def __init__(self, key):
        self.fernet = Fernet(key)

    def save_config(self, config_data):
        json_data = json.dumps(config_data).encode()
        encrypted_data = self.fernet.encrypt(json_data)
        with open(self.CONFIG_FILE, 'wb') as f:
            f.write(encrypted_data)

    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            return None
        with open(self.CONFIG_FILE, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = self.fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())

    @staticmethod
    def generate_key():
        return Fernet.generate_key()
