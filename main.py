import subprocess
import sys
import os


def run_app_desktop():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Usar el Python del entorno virtual
    venv_python = os.path.join(current_dir, "venv", "bin", "python")

    if os.path.exists(venv_python):
        python_executable = venv_python
        print(f"✅ Usando Python del entorno virtual")
    else:
        print("⚠️ Usando Python del sistema")
        python_executable = sys.executable

    # Cambiar al directorio app-desktop y ejecutar
    app_desktop_path = os.path.join(current_dir, "app-desktop")

    # Crear un script temporal en app-desktop
    temp_script = os.path.join(app_desktop_path, "run_app.py")

    script_content = '''
from PySide6.QtWidgets import QApplication
from services.config_service import ConfigService
from gui.login_window import LoginWindow
import sys

def main():
    app = QApplication(sys.argv)

    # Crear el config_service (sin encriptación)
    config_service = ConfigService("config.json")

    # Verificar si existe configuración, si no crear una por defecto
    if not config_service.load_config():
        print("🔧 Creando archivo de configuración por defecto...")
        config_service.create_default_config()

    # Pasar el config_service a LoginWindow
    login_window = LoginWindow(config_service)
    login_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

    try:
        # Escribir el script temporal
        with open(temp_script, 'w') as f:
            f.write(script_content)

        print(f"🚀 Ejecutando aplicación desktop...")
        subprocess.run([python_executable, temp_script], check=True)

        # Limpiar el script temporal
        os.remove(temp_script)

    except Exception as e:
        print(f"❌ Error: {e}")
        # Limpiar en caso de error
        if os.path.exists(temp_script):
            os.remove(temp_script)


if __name__ == "__main__":
    run_app_desktop()
