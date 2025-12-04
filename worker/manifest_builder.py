# ============================================================
#   SEMEFO — manifest_builder.py (FINAL)
#   Generación de manifest por cámara y día.
#   Compatible 100% con tasks.py (usa campo "ruta")
# ============================================================

import os
import json
import datetime
from glob import glob
from dotenv import load_dotenv
from .celery_app import celery_app

load_dotenv()

# Ruta raíz del SMB (montado en el contenedor)
SMB_ROOT = os.getenv("SMB_MOUNT", "/mnt/wave").rstrip("/")

# UUID del WAVE configurado en .env
GRABADOR_UUID = os.getenv("GRABADOR_UUID", "UNKNOWN_UUID")

# Fragmentos MKV
EXT_FRAGMENTO = "*.mkv"


# ============================================================
#   UTILIDADES
# ============================================================

def extraer_timestamp(filename):
    """
    Convierte nombre como: 1764662554731_76000.mkv
    a un rango de 1 minuto basado en su timestamp UNIX.
    """
    try:
        base = filename.split("_")[0]  # ej: 1764662554731
        ts_ms = int(base)
        inicio = datetime.datetime.fromtimestamp(ts_ms / 1000)
        fin = inicio + datetime.timedelta(minutes=1)
        return inicio, fin
    except:
        return None, None


def cargar_manifest(path_manifest):
    if os.path.exists(path_manifest):
        try:
            with open(path_manifest, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def guardar_manifest(path_manifest, data):
    os.makedirs(os.path.dirname(path_manifest), exist_ok=True)
    with open(path_manifest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def ruta_manifest(mac, fecha):
    yyyy = fecha.strftime("%Y")
    mm = fecha.strftime("%m")
    dd = fecha.strftime("%d")

    return os.path.join(
        SMB_ROOT,
        "manifests",
        GRABADOR_UUID,
        mac,
        yyyy,
        dd,
        "manifest.json"
    )


# ============================================================
#   TAREA CELERY — GENERAR MANIFEST
# ============================================================

@celery_app.task(name="tasks.generar_manifest", queue="manifest")
def generar_manifest(mac_camara, fecha_iso):
    """
    mac_camara → nombre de carpeta en hi_quality
    fecha_iso  → 'YYYY-MM-DD'
    """
    fecha = datetime.datetime.fromisoformat(fecha_iso).date()

    # Carpeta del día en el SMB
    ruta_frag = os.path.join(
        SMB_ROOT,
        GRABADOR_UUID,
        "hi_quality",
        mac_camara,
        fecha.strftime("%Y"),
        fecha.strftime("%m"),
        fecha.strftime("%d")
    )

    if not os.path.isdir(ruta_frag):
        print(f"[MANIFEST] No existe carpeta de fragmentos: {ruta_frag}")
        return False

    path_manifest = ruta_manifest(mac_camara, fecha)
    manifest = cargar_manifest(path_manifest)

    manifest.setdefault("uuid", GRABADOR_UUID)
    manifest.setdefault("fecha", fecha_iso)
    manifest.setdefault("camara_mac", mac_camara)
    manifest.setdefault("archivos", [])

    ya_registrados = {a["archivo"] for a in manifest["archivos"]}

    nuevos = []

    for file_path in sorted(glob(os.path.join(ruta_frag, EXT_FRAGMENTO))):
        archivo = os.path.basename(file_path)

        if archivo in ya_registrados:
            continue

        inicio, fin = extraer_timestamp(archivo)
        if inicio is None:
            continue

        entry = {
            "archivo": archivo,
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
            "ruta": file_path  # <===== RUTA ABSOLUTA COMPATIBLE CON tasks.py
        }

        manifest["archivos"].append(entry)
        nuevos.append(entry)

    guardar_manifest(path_manifest, manifest)

    print(f"[MANIFEST] Guardado → {path_manifest}")
    print(f"[MANIFEST] Nuevos fragmentos: {len(nuevos)}")

    return True
