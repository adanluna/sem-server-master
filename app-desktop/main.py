import sys
import os
from PySide6.QtWidgets import QApplication
from services.config_service import ConfigService
from gui.login_window import LoginWindow
from dotenv import load_dotenv

# Agregar el directorio padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))


def main():
    app = QApplication(sys.argv)
    
    # Intentar obtener la clave de las variables de entorno
    encryption_key = os.getenv("CONFIG_ENCRYPTION_KEY")
    
    if not encryption_key:
        # Si no existe, generar una nueva y mostrarla
        encryption_key = ConfigService.generate_key()
        print(f"⚠️  Clave de encriptación generada: {encryption_key.decode()}")
        print("💡 Agrega esta línea a tu archivo .env.local:")
        print(f"CONFIG_ENCRYPTION_KEY={encryption_key.decode()}")
    else:
        # Convertir string a bytes si viene del .env
        encryption_key = encryption_key.encode()
    
    # Crear el config_service con la clave
    config_service = ConfigService(encryption_key)
    
    # Pasar el config_service a LoginWindow
    login_window = LoginWindow(config_service)
    login_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
