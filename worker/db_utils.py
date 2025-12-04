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


# ============================================================
#   API: SESION_ARCHIVOS
# ============================================================

def registrar_sesion_archivo(sesion_id, tipo_archivo, ruta_original):
    try:
        # Verificar si ya existe
        response = requests.get(f"{server_url}/sesiones/{sesion_id}/archivos")
        response.raise_for_status()
        archivos = response.json()

        ya_existe = any(a["tipo_archivo"] == tipo_archivo for a in archivos)
        if ya_existe:
            return

        payload = {
            "sesion_id": sesion_id,
            "tipo_archivo": tipo_archivo,
            "ruta_original": ruta_original,
            "conversion_completa": False,
        }
        response = requests.post(f"{server_url}/archivos/", json=payload)
        response.raise_for_status()
        return response.json().get("id")
    except Exception as e:
        print(f"❌ Error registrando archivo en API: {e}")
        return None


def finalizar_sesion_archivo(sesion_id, tipo_archivo, ruta_convertida):
    """
    Marca el archivo como completado y actualiza toda su información.
    """
    try:
        payload = {
            "estado": "completado",
            "mensaje": f"Conversión finalizada: {ruta_convertida}",
            "fecha_finalizacion": True,
            "ruta_convertida": ruta_convertida,
            "conversion_completa": True
        }

        response = requests.put(
            f"{server_url}/archivos/{sesion_id}/{tipo_archivo}/actualizar_estado",
            json=payload
        )
        response.raise_for_status()
        return True

    except Exception as e:
        print(f"❌ Error actualizando archivo de sesión: {e}")
        return False
