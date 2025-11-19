import os
import json
import subprocess
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

# ======================================================
#  CONFIGURACIÓN DE RUTAS
# ======================================================

# Ruta segura dentro del volumen compartido
BASE_LOG_DIR = "/storage/logs"
os.makedirs(BASE_LOG_DIR, exist_ok=True)

LOG_LOCAL = os.path.join(BASE_LOG_DIR, "manifest.log")

# ======================================================
#  CONFIGURACIÓN API
# ======================================================

API_HOST = os.getenv("API_SERVER_URL", "192.168.1.11:8000")
API_URL = f"http://{API_HOST}"
LOG_ENDPOINT = f"{API_URL}/logs"


# ======================================================
#  LOG LOCAL
# ======================================================
def log_local(msg):
    """Log técnico local dentro de /storage/logs/"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_LOCAL, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


# ======================================================
#  LOG A API
# ======================================================
def log_event(tipo, descripcion, usuario="system"):
    """Envía log técnico a local + log lógico a API"""
    log_local(f"{tipo}: {descripcion}")

    try:
        requests.post(
            LOG_ENDPOINT,
            json={
                "tipo_evento": tipo,
                "descripcion": descripcion,
                "usuario_ldap": usuario
            },
            timeout=2
        )
    except Exception:
        log_local("ERROR enviando log a API")


# ======================================================
#  FFPROBE
# ======================================================
def ffprobe_info(path):
    """Obtiene creation_time y duración real del archivo MKV"""
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

        # --- CREATION TIME ---
        try:
            creation = data["format"]["tags"]["creation_time"]
        except:
            creation = datetime.utcfromtimestamp(
                os.path.getmtime(path)
            ).isoformat() + "Z"

        # --- DURACIÓN ---
        try:
            dur = float(data["format"]["duration"])
        except:
            dur = 0.0

        return creation, dur

    except Exception as e:
        log_event("manifest_error",
                  f"ffprobe falló en {path}: {e}")
        return None, None


# ======================================================
#  UTILIDADES MANIFEST
# ======================================================
def cargar_manifest(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_manifest(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ======================================================
#  FUNCIÓN PRINCIPAL
# ======================================================
def actualizar_manifest(carpeta_dia, mac):
    log_event("manifest_inicio",
              f"Iniciando manifest en {carpeta_dia} para cámara {mac}")

    manifest_path = os.path.join(carpeta_dia, "manifest.json")
    archivos_fs = [f for f in os.listdir(carpeta_dia)
                   if f.endswith(".mkv")]

    manifest = cargar_manifest(manifest_path)
    nuevos_count = 0

    if manifest is None:
        log_event("manifest_nuevo",
                  f"Creando manifest nuevo para {mac}")
        manifest = {
            "fecha": carpeta_dia.split(os.sep)[-1],
            "camara_mac": mac,
            "archivos": []
        }
    else:
        log_event("manifest_existente",
                  f"Manifest existente: {manifest_path}")

    archivos_indexados = {item["archivo"] for item in manifest["archivos"]}

    for archivo in archivos_fs:
        if archivo in archivos_indexados:
            continue

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

    manifest["archivos"].sort(key=lambda x: x["inicio"])
    guardar_manifest(manifest_path, manifest)

    log_event("manifest_generado",
              f"Manifest actualizado. Archivos nuevos: {nuevos_count}")

    return manifest
