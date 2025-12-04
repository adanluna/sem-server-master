# ============================================================
#   worker/job_api_client.py (FINAL)
#   Comunicación del Worker → API Master
# ============================================================

import requests
import os

# Usar URL exacta del .env sin modificarla
API_URL = os.getenv("API_SERVER_URL", "http://172.31.82.2:8000")


# ============================================================
#   JOBS
# ============================================================

def registrar_job(numero_expediente, id_sesion, tipo, archivo):
    try:
        response = requests.post(
            f"{API_URL}/jobs/crear",
            json={
                "numero_expediente": numero_expediente,
                "id_sesion": id_sesion,
                "tipo": tipo,
                "archivo": archivo,
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("job_id")

    except Exception as e:
        print(f"❌ Error registrando job en API: {e}")
        return None


def actualizar_job(job_id, estado=None, resultado=None, error=None):
    try:
        payload = {}
        if estado:
            payload["estado"] = estado
        if resultado:
            payload["resultado"] = resultado
        if error:
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

def finalizar_archivo(id_sesion, tipo_archivo, ruta_convertida):
    """
    Marca un archivo como completado.
    """
    try:
        payload = {
            "estado": "completado",
            "mensaje": f"Archivo finalizado correctamente: {ruta_convertida}",
            "fecha_finalizacion": True,
            "ruta_convertida": ruta_convertida,
            "conversion_completa": True
        }

        response = requests.put(
            f"{API_URL}/archivos/{id_sesion}/{tipo_archivo}/actualizar_estado",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True

    except Exception as e:
        print(f"❌ Error finalizando archivo {tipo_archivo}: {e}")
        return False


def registrar_archivo(id_sesion, tipo_archivo, ruta_original, ruta_convertida=None):
    """
    Registra un archivo si no existe.
    """
    try:
        # Listar archivos existentes
        response = requests.get(
            f"{API_URL}/sesiones/{id_sesion}/archivos",
            timeout=10
        )
        response.raise_for_status()
        archivos = response.json()

        # Validar existencia previa
        ya_existe = any(a["tipo_archivo"] == tipo_archivo for a in archivos)
        if ya_existe:
            return

        payload = {
            "sesion_id": id_sesion,
            "tipo_archivo": tipo_archivo,
            "ruta_original": ruta_original,
            "ruta_convertida": ruta_convertida or ruta_original,
            "conversion_completa": False
        }

        response = requests.post(
            f"{API_URL}/archivos/",
            json=payload,
            timeout=10
        )
        response.raise_for_status()

        return response.json().get("id")

    except Exception as e:
        print(
            f"❌ Error registrando archivo {tipo_archivo} en sesión {id_sesion}: {e}")
        return None


def registrar_pausas_auto(sesion_id, pausas):
    url = f"{API_URL}/sesiones/{sesion_id}/pausas_auto"
    payload = {"pausas": pausas}

    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print("[API] Error enviando pausas auto:", e)
        return False
