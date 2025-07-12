import json
import os
from typing import Dict, Any, Optional


class ConfigService:
    def __init__(self, config_file: str = "config.json"):
        """
        Servicio de configuración usando archivo JSON simple
        """
        # El archivo de configuración estará en el directorio app-desktop
        # Subir desde services/ a app-desktop/
        app_dir = os.path.dirname(os.path.dirname(__file__))
        self.config_path = os.path.join(app_dir, config_file)
        print(f"📁 Archivo de configuración: {self.config_path}")

    def load_config(self) -> Optional[Dict[str, Any]]:
        """Cargar configuración desde archivo JSON"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    config = json.load(file)
                    print(f"✅ Configuración cargada desde {self.config_path}")
                    return config
            else:
                print(
                    f"⚠️ No existe archivo de configuración: {self.config_path}")
                return None
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            return None

    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """Guardar configuración en archivo JSON"""
        try:
            # Crear el directorio si no existe
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Guardar con formato legible
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(config_data, file, indent=4, ensure_ascii=False)

            print(f"✅ Configuración guardada en {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Error guardando configuración: {e}")
            return False

    def create_default_config(self) -> bool:
        """Crear archivo de configuración con valores por defecto"""
        from datetime import datetime

        # Cargar desde .env para los valores por defecto
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(
            self.config_path), "..", ".env")
        load_dotenv(dotenv_path=env_path)

        default_config = {
            "dispositivo": {
                "tablet_id": "",
                "plancha": ""
            },
            "camaras": {
                "camera1_ip": "",
                "camera2_ip": ""
            },
            "api": {
                "server_ip": "192.168.1.220:8000"  # IP por defecto del API
            },
            "ldap": {
                "server": os.getenv("LDAP_SERVER_IP", ""),
                "port": os.getenv("LDAP_PORT", "389"),
                "domain": os.getenv("LDAP_DOMAIN", "")
            },
            "version": "1.0.0",
            "fecha_creacion": datetime.now().isoformat()
        }

        print(f"🔧 Creando configuración por defecto:")
        print(f"   LDAP Server: {default_config['ldap']['server']}")
        print(f"   LDAP Domain: {default_config['ldap']['domain']}")
        print(f"   API Server: {default_config['api']['server_ip']}")

        return self.save_config(default_config)
