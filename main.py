import subprocess
import sys
import os
import shutil


def main():
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

    # Copiar styles.qss si existe
    styles_source = os.path.join(current_dir, "styles.qss")
    styles_dest = os.path.join(app_desktop_path, "styles.qss")

    if os.path.exists(styles_source):
        try:
            shutil.copy2(styles_source, styles_dest)
            print("✅ styles.qss copiado a app-desktop")
        except Exception as e:
            print(f"⚠️ Error copiando styles.qss: {e}")
    else:
        print("⚠️ styles.qss no encontrado en directorio raíz")

    # Copiar logo.png si existe
    logo_source = os.path.join(current_dir, "logo.png")
    logo_dest = os.path.join(app_desktop_path, "logo.png")

    if os.path.exists(logo_source):
        try:
            shutil.copy2(logo_source, logo_dest)
            print("✅ logo.png copiado a app-desktop")
        except Exception as e:
            print(f"⚠️ Error copiando logo.png: {e}")
    else:
        print("⚠️ logo.png no encontrado en directorio raíz")

    # Crear un script temporal en app-desktop
    temp_script = os.path.join(app_desktop_path, "run_app.py")

    script_content = '''
from PySide6.QtWidgets import QApplication
from services.config_service import ConfigService
from gui.login_window import LoginWindow
import sys
import os

def load_styles():
    """Cargar estilos desde styles.qss"""
    try:
        with open("styles.qss", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("⚠️ Archivo styles.qss no encontrado")
        return ""
    except Exception as e:
        print(f"⚠️ Error cargando estilos: {e}")
        return ""

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SEMEFO Desktop")

    # Cargar estilos globales
    stylesheet = load_styles()
    if stylesheet:
        app.setStyleSheet(stylesheet)
        print("✅ Estilos cargados desde styles.qss")
    else:
        print("⚠️ Usando estilos por defecto")

    # Crear el config_service
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

        # Cambiar al directorio app-desktop antes de ejecutar
        original_cwd = os.getcwd()
        os.chdir(app_desktop_path)

        result = subprocess.run([python_executable, "run_app.py"], check=True)

        # Volver al directorio original
        os.chdir(original_cwd)

        # Limpiar el script temporal
        if os.path.exists(temp_script):
            os.remove(temp_script)

    except Exception as e:
        print(f"❌ Error: {e}")
        # Volver al directorio original
        try:
            os.chdir(original_cwd)
        except:
            pass
        # Limpiar en caso de error
        if os.path.exists(temp_script):
            os.remove(temp_script)


if __name__ == "__main__":
    main()
