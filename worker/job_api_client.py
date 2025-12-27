# ============================================================
#   worker/job_api_client.py (2025 - AUTH + ROBUSTO)
#   Comunicación Worker → API Master (service-token)
# ============================================================

import os
import time
import requests
from datetime import datetime, timezone
import base64
import json


# ============================================================
# NORMALIZAR API_URL
# ============================================================
def _normalizar_api_url():
    raw = os.getenv("API_SERVER_URL", "http://fastapi_app:8000").rstrip("/")
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "http://" + raw
    return raw.rstrip("/")


API_URL = _normalizar_api_url()

WORKER_CLIENT_ID = os.getenv("WORKER_CLIENT_ID", "").strip()
WORKER_CLIENT_SECRET = os.getenv("WORKER_CLIENT_SECRET", "").strip()

# Cache simple en memoria
_TOKEN_CACHE = {
    "access_token": None,
    "expires_at_ts": 0,  # epoch seconds
}


def _jwt_exp_ts(token: str) -> int | None:
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(
            payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        return int(exp) if exp else None
    except Exception:
        return None


# ============================================================
# AUTH
# ============================================================
def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_service_token(force_refresh: bool = False) -> str | None:
    """
    Obtiene token de servicio (JWT access) y lo cachea.
    """
    now = time.time()

    if not force_refresh:
        token = _TOKEN_CACHE.get("access_token")
        exp = _TOKEN_CACHE.get("expires_at_ts", 0)
        # margen 30s
        if token and now < (exp - 30):
            return token

    if not WORKER_CLIENT_ID or not WORKER_CLIENT_SECRET:
        print("❌ WORKER_CLIENT_ID/WORKER_CLIENT_SECRET no configurados en .env")
        return None

    try:
        r = requests.post(
            f"{API_URL}/auth/service-token",
            json={
                "client_id": WORKER_CLIENT_ID,
                "client_secret": WORKER_CLIENT_SECRET
            },
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token")
        if not token:
            print("❌ API no devolvió access_token para service-token")
            return None

        # Si no tenemos exp decodificado, hacemos un TTL conservador (23h)
        # (Si luego quieres, decodificamos JWT sin verificar firma solo para exp)
        _TOKEN_CACHE["access_token"] = token
        exp_ts = _jwt_exp_ts(token)
        _TOKEN_CACHE["expires_at_ts"] = exp_ts if exp_ts else (
            now + 3600)  # fallback 1h

        return token

    except Exception as e:
        print(f"❌ Error obteniendo service-token: {e}")
        return None


def _auth_headers() -> dict:
    token = _get_service_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _request(method: str, url: str, *, json=None, timeout=10):
    """
    Wrapper con:
    - headers auth
    - retry único si 401
    """
    headers = {"Content-Type": "application/json", **_auth_headers()}
    r = requests.request(method, url, json=json,
                         timeout=timeout, headers=headers)

    if r.status_code == 401:
        # refresh token y retry 1 vez
        token = _get_service_token(force_refresh=True)
        if token:
            headers = {"Content-Type": "application/json",
                       "Authorization": f"Bearer {token}"}
            r = requests.request(method, url, json=json,
                                 timeout=timeout, headers=headers)

    r.raise_for_status()
    return r


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

        r = _request("POST", f"{API_URL}/jobs/crear", json=payload, timeout=10)
        return r.json().get("job_id")

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

        _request("PUT", f"{API_URL}/jobs/{job_id}/actualizar",
                 json=payload, timeout=10)
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
    Intenta evitar duplicados consultando la lista.
    """
    try:
        existentes = []
        try:
            rr = _request(
                "GET", f"{API_URL}/sesiones/{id_sesion}/archivos", timeout=10)
            existentes = rr.json() or []
        except Exception:
            # Si no existe endpoint o falla, seguimos e intentamos POST
            existentes = []

        if any(a.get("tipo_archivo") == tipo_archivo for a in existentes):
            return None

        payload = {
            "sesion_id": id_sesion,
            "tipo_archivo": tipo_archivo,
            "ruta_original": ruta_original,
            "ruta_convertida": ruta_convertida or ruta_original,
            "estado": estado,
            "conversion_completa": False
        }

        r = _request("POST", f"{API_URL}/archivos/", json=payload, timeout=10)
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
            # ✅ datetime ISO (no bool)
            "fecha_finalizacion": _utcnow_iso(),
            "ruta_convertida": ruta,
            "conversion_completa": True
        }

        _request(
            "PUT", f"{API_URL}/archivos/{sesion_id}/{tipo_archivo}/actualizar_estado", json=payload, timeout=10)
        return True

    except Exception as e:
        print(f"❌ Error finalizando archivo {tipo_archivo}: {e}")
        return False


# ============================================================
#   PAUSAS AUTO
# ============================================================
def registrar_pausas_auto(sesion_id, pausas):
    """
    Registra pausas detectadas automáticamente.
    Endpoint correcto: /sesiones/{sesion_id}/pausas_detectadas
    """
    try:
        _request(
            "POST",
            f"{API_URL}/sesiones/{sesion_id}/pausas_detectadas",
            json={"pausas": pausas},
            timeout=10
        )
        return True

    except Exception as e:
        print(f"❌ Error registrando pausas auto: {e}")
        return False
