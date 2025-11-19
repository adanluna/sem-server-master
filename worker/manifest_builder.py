import os
import json
import subprocess
from datetime import datetime
import requests
from dotenv import load_dotenv
LOCAL_LOG_PATH = "/opt/semefo/logs/manifest.log"
load_dotenv()

# ============================================
#  CONFIGURACIÓN API Y LOGS
# ============================================

API_HOST = os.getenv("API_SERVER_URL", "192.168.1.11:8000")
API_URL = f"http://{API_HOST}"
LOG_ENDPOINT = f"{API_URL}/logs"

LOG_LOCAL = "/opt/semefo/logs/manifest.log"
os.makedirs(os.path.dirname(LOG_LOCAL), exist_ok=True)


def log_local(msg):
    try:
        with open(LOG_LOCAL, "a") as f:
            f.write(msg + "\n")
    except:
        pass


def log_event(tipo, descripcion, usuario="system"):
    # Log técnico local SIEMPRE
    log_local(f"{tipo}: {descripcion}")

    # Log importante → BD vía FastAPI
    try:
        requests.post(
            f"http://{API_URL}/logs",
            json={
                "tipo_evento": tipo,
                "descripcion": descripcion,
                "usuario_ldap": usuario
            },
            timeout=2
        )
    except Exception:
        # No romper proceso por falla de red/API
        log_local(f"ERROR enviando log a API")

# ============================================
#  FFPROBE
# ============================================


def ffprobe_info(path):
    """
    Obtiene creation_time y duración real del archivo.
    Si no hay metadata, usa timestamps del sistema.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_entries", "format_tags=creation_time,format=duration",
                path
            ],
            capture_output=True, text=True
        )

        data = json.loads(result.stdout or "{}")

        creation = None
        dur = None

        # --- CREATION TIME ---
        try:
            creation = data["format"]["tags"]["creation_time"]
        except:
            # fallback → usar mtime
            creation = datetime.utcfromtimestamp(
                os.path.getmtime(path)
            ).isoformat() + "Z"

        # --- DURACION ---
        try:
            dur = float(data["format"]["duration"])
        except:
            # fallback → duración desconocida
            dur = 0.0

        return creation, dur

    except Exception as e:
        log_event("manifest_error", f"ffprobe falló en {path}: {e}")
        return None, None


# ============================================
#  MANIFEST UTILIDADES
# ============================================
def cargar_manifest(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_manifest(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ============================================
#  MAIN FUNCTION: ACTUALIZAR MANIFEST
# ============================================
def actualizar_manifest(carpeta_dia, mac):
    # 🟩 1. Log de inicio (local + BD)
    log_event("manifest_inicio",
              f"Iniciando manifest en {carpeta_dia} para cámara {mac}")

    manifest_path = os.path.join(carpeta_dia, "manifest.json")
    archivos_fs = [f for f in os.listdir(carpeta_dia) if f.endswith(".mkv")]

    manifest = cargar_manifest(manifest_path)
    nuevos_count = 0

    if manifest is None:
        log_event("manifest_nuevo",
                  f"Creando manifest nuevo para {mac} en {carpeta_dia}")
        manifest = {
            "fecha": carpeta_dia.split(os.sep)[-1],
            "camara_mac": mac,
            "archivos": []
        }
    else:
        log_event("manifest_existente",
                  f"Manifest existente detectado: {manifest_path}")

    archivos_indexados = {item["archivo"] for item in manifest["archivos"]}

    for archivo in archivos_fs:
        if archivo in archivos_indexados:
            continue  # Ya está indexado (no duplicar)

        ruta = os.path.join(carpeta_dia, archivo)

        creation, dur = ffprobe_info(ruta)
        if not creation:
            continue

        dt_inicio = datetime.fromisoformat(creation.replace("Z", ""))
        dt_fin = dt_inicio.timestamp() + dur

        manifest["archivos"].append({
            "archivo": archivo,
            "ruta": ruta.replace("\\", "/"),
            "inicio": creation,
            "fin": datetime.utcfromtimestamp(dt_fin).isoformat() + "Z",
            "duracion": dur,
            "creado_fs": datetime.utcfromtimestamp(os.path.getctime(ruta)).isoformat() + "Z",
            "modificado_fs": datetime.utcfromtimestamp(os.path.getmtime(ruta)).isoformat() + "Z"
        })

        nuevos_count += 1

    # Ordenar por inicio
    manifest["archivos"].sort(key=lambda x: x["inicio"])

    guardar_manifest(manifest_path, manifest)

    # 🟩 2. Log final
    log_event("manifest_generado",
              f"Manifest actualizado para {mac}. Archivos nuevos: {nuevos_count}")

    return manifest


def log_local(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOCAL_LOG_PATH), exist_ok=True)
    with open(LOCAL_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
