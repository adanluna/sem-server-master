# ============================================================
#   worker/db_utils.py (FINAL)
#   Utilidades de comunicación con API + manejo de rutas
# ============================================================

import os
import requests

# Leer URL del servidor API exactamente como viene en el .env
API_URL = os.getenv("API_SERVER_URL", "http://172.31.82.2:8000")


# ============================================================
#   NORMALIZAR RUTA SMB
# ============================================================

def normalizar_ruta(r):
    """
    Limpia rutas SMB para evitar // o \
    """
    if not r:
        return r
    return r.replace("\\", "/").replace("//", "/")


# ============================================================
#   REGISTRO DE ARCHIVOS EN API
# ============================================================

def registrar_sesion_archivo(sesion_id, tipo_archivo, ruta_original):
    """
    Registra un archivo si todavía no existe en la API.
    """
    try:
        # Listar archivos existentes
        response = requests.get(
            f"{API_URL}/sesiones/{sesion_id}/archivos",
            timeout=10
        )
        response.raise_for_status()
        archivos = response.json()

        # Validar si ya existe
        ya_existe = any(a["tipo_archivo"] == tipo_archivo for a in archivos)
        if ya_existe:
            return None

        payload = {
            "sesion_id": sesion_id,
            "tipo_archivo": tipo_archivo,
            "ruta_original": normalizar_ruta(ruta_original),
            "conversion_completa": False,
        }

        response = requests.post(
            f"{API_URL}/archivos/",
            json=payload,
            timeout=10
        )
        response.raise_for_status()

        return response.json().get("id")

    except Exception as e:
        print(f"❌ Error registrando archivo en API: {e}")
        return None


def finalizar_sesion_archivo(sesion_id, tipo_archivo, ruta_convertida):
    """
    Marca el archivo como finalizado en la API.
    """
    try:
        payload = {
            "estado": "completado",
            "mensaje": f"Archivo procesado correctamente: {ruta_convertida}",
            "fecha_finalizacion": True,
            "ruta_convertida": normalizar_ruta(ruta_convertida),
            "conversion_completa": True
        }

        response = requests.put(
            f"{API_URL}/archivos/{sesion_id}/{tipo_archivo}/actualizar_estado",
            json=payload,
            timeout=10
        )
        response.raise_for_status()

        return True

    except Exception as e:
        print(f"❌ Error actualizando archivo en API: {e}")
        return False
