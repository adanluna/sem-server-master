# ============================================================
#   worker/job_api_client.py (REVISION 2025 - COMPLETO Y ROBUSTO)
#   Comunicación Worker → API Master
# ============================================================

import requests
import os


# ============================================================
# NORMALIZAR API_URL
# ============================================================

def _normalizar_api_url():
    raw = os.getenv("API_SERVER_URL", "http://fastapi_app:8000").rstrip("/")

    # Agregar http:// si falta
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "http://" + raw

    return raw.rstrip("/")


API_URL = _normalizar_api_url()


# ============================================================
#   JOBS
# ============================================================

def registrar_job(numero_expediente, id_sesion, tipo, archivo):
    """
    Crear un nuevo job en el master.
    """
    try:
        payload = {
            "numero_expediente": numero_expediente,
            "id_sesion": id_sesion,
            "tipo": tipo,
            "archivo": archivo,
            "estado": "pendiente",
            "resultado": None,
            "error": None
        }

        response = requests.post(
            f"{API_URL}/jobs/crear",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("job_id")

    except Exception as e:
        print(f"❌ Error registrando job en API: {e}")
        return None


def actualizar_job(job_id, estado=None, resultado=None, error=None):
    """
    Actualizar estado o errores de un job existente.
    """
    try:
        payload = {}

        if estado is not None:
            payload["estado"] = estado
        if resultado is not None:
            payload["resultado"] = resultado
        if error is not None:
            payload["error"] = error

        response = requests.put(
            f"{API_URL}/jobs/{job_id}/actualizar",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True

    except Exception as e:
        print(f"❌ Error actualizando job {job_id}: {e}")
        return False


# ============================================================
#   ARCHIVOS
# ============================================================

def registrar_archivo(id_sesion, tipo_archivo, ruta_original, ruta_convertida=None, estado="procesando"):
    """
    Registrar archivo en `sesion_archivos`.
    Evita duplicados.
    """
    try:
        # Obtener lista existente
        r = requests.get(
            f"{API_URL}/sesiones/{id_sesion}/archivos",
            timeout=10
        )
        r.raise_for_status()
        existentes = r.json()

        # Ver si YA existe
        if any(a["tipo_archivo"] == tipo_archivo for a in existentes):
            return

        payload = {
            "sesion_id": id_sesion,
            "tipo_archivo": tipo_archivo,
            "ruta_original": ruta_original,
            "ruta_convertida": ruta_convertida or ruta_original,
            "estado": estado,
            "conversion_completa": False
        }

        r = requests.post(
            f"{API_URL}/archivos/",
            json=payload,
            timeout=10
        )
        r.raise_for_status()
        return r.json().get("id")

    except Exception as e:
        print(f"❌ Error registrando archivo {tipo_archivo}: {e}")
        return None


def finalizar_archivo(sesion_id, tipo_archivo, ruta):
    """
    Marca un archivo como completado.
    """
    try:
        payload = {
            "estado": "completado",
            "mensaje": f"Archivo finalizado correctamente: {ruta}",
            "fecha_finalizacion": True,
            "ruta_convertida": ruta,
            "conversion_completa": True
        }

        r = requests.put(
            f"{API_URL}/archivos/{sesion_id}/{tipo_archivo}/actualizar_estado",
            json=payload,
            timeout=10
        )
        r.raise_for_status()
        return True

    except Exception as e:
        print(f"❌ Error finalizando archivo {tipo_archivo}: {e}")
        return False


def registrar_pausas_auto(sesion_id, pausas):
    """
    Registra pausas detectadas automáticamente.
    """
    try:
        r = requests.post(
            f"{API_URL}/sesiones/{sesion_id}/pausas_auto",
            json={"pausas": pausas},
            timeout=10
        )
        return r.status_code == 200

    except Exception as e:
        print(f"❌ Error registrando pausas auto: {e}")
        return False
