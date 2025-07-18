# worker/job_api_client.py
import requests
import os

# Obtener URL del API desde .env
server_url = os.getenv("API_SERVER_URL", "http://fastapi_app:8000")

# Agregar http:// si no está presente
if not server_url.startswith(('http://', 'https://')):
    server_url = f"http://{server_url}"

API_URL = server_url


def registrar_job(numero_expediente, id_sesion, tipo, archivo):
    try:
        response = requests.post(f"{API_URL}/jobs/crear", json={
            "numero_expediente": numero_expediente,
            "id_sesion": id_sesion,
            "tipo": tipo,
            "archivo": archivo,
        })
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
            f"{API_URL}/jobs/{job_id}/actualizar", json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error actualizando job {job_id} en API: {e}")
        return False


def finalizar_archivo(id_sesion, tipo_archivo, ruta_convertida):
    """
    Marca un archivo como completado y actualiza su estado en la API.
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
            f"{API_URL}/archivos/{id_sesion}/{tipo_archivo}/actualizar_estado",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(
            f"❌ Error finalizando archivo {tipo_archivo} en sesión {id_sesion}: {e}")
        return False


def registrar_archivo(id_sesion, tipo_archivo, ruta_original):
    """
    Registra un archivo en la API si aún no existe.
    """
    try:
        # Verificar si ya existe
        response = requests.get(f"{API_URL}/sesiones/{id_sesion}/archivos")
        response.raise_for_status()
        archivos = response.json()

        ya_existe = any(a["tipo_archivo"] == tipo_archivo for a in archivos)
        if ya_existe:
            return

        payload = {
            "sesion_id": id_sesion,
            "tipo_archivo": tipo_archivo,
            "ruta_original": ruta_original,
            "conversion_completa": False
        }

        response = requests.post(f"{API_URL}/archivos/", json=payload)
        response.raise_for_status()
        return response.json().get("id")
    except Exception as e:
        print(
            f"❌ Error registrando archivo {tipo_archivo} en sesión {id_sesion}: {e}")
        return None
