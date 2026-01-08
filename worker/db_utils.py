# worker/db_utils.py

import os
import shutil
import requests

# Leer y validar la URL del servidor API
server_url = os.getenv("API_SERVER_URL", "fastapi_app:8000")

# Agregar http:// si no está presente
if not server_url.startswith(("http://", "https://")):
    server_url = f"http://{server_url}"


# ============================================================
#   UTILIDADES DE ARCHIVOS Y DIRECTORIOS
# ============================================================

def ensure_dir(path):
    """
    Crea un directorio si no existe.
    """
    os.makedirs(path, exist_ok=True)


def limpiar_temp(path):
    """
    Elimina carpeta temporal y la vuelve a crear limpia.
    """
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)


def normalizar_ruta(path):
    """
    Normaliza rutas para evitar problemas de backslashes \ tipo Windows.
    """
    return path.replace("\\", "/")
