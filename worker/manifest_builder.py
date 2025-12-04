# ============================================================
#   SEMEFO — manifest_builder.py (FINAL)
#   Generación y actualización de manifests por cámara
# ============================================================

import os
import json
import datetime
from glob import glob
from dotenv import load_dotenv
from .celery_app import celery_app

load_dotenv()

# ============================================================
#   CONFIGURACIÓN GLOBAL
# ============================================================

# Directorio SMB donde están los MKV del grabador
SMB_ROOT = os.getenv("SMB_MOUNT", "/mnt/wave")

# UUID del grabador (desde .env)
GRABADOR_UUID = os.getenv("GRABADOR_UUID", "UNKNOWN_UUID")

# Carpeta fija donde están los fragmentos de video
QUALITY_FOLDER = "hi_quality"

# Extensión de los fragmentos generados por Hanwha / Marshall
EXT_FRAGMENTO = "*.mkv"


# ============================================================
#   UTILIDADES
# ============================================================

def extraer_timestamp(filename):
    """
    Extrae la fecha y hora del nombre del archivo MKV.
    Formato esperado (Hanwha/Marshall):
       1764662554731_76000.mkv

    Donde el nombre NO incluye fecha, pero la fecha se obtiene
    desde la estructura de carpetas (YYYY/MM/DD/HH).
    """
    try:
        partes = filename.split("_")
        hora_str = partes[-1].split(".")[0]   # ej: "76000"
        HH = int(hora_str[0:2])
        MM = int(hora_str[2:4])

        # La fecha verdadera la determinamos en generar_manifest()
        return HH, MM

    except Exception:
        return None, None


def cargar_manifest(path_manifest):
    """Carga manifest existente si existe; en caso contrario regresa dict vacío."""
    if os.path.exists(path_manifest):
        try:
            with open(path_manifest, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def guardar_manifest(path_manifest, data):
    """Guarda manifest formateado en JSON."""
    os.makedirs(os.path.dirname(path_manifest), exist_ok=True)
    with open(path_manifest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def calcular_ruta_manifest(mac, fecha):
    """Genera la ruta del manifest según arquitectura oficial."""
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
#   TAREA CELERY – GENERAR / ACTUALIZAR MANIFEST
# ============================================================

@celery_app.task(name="tasks.generar_manifest", queue="manifest")
def generar_manifest(mac_camara, fecha_iso):
    """
    Genera o actualiza el manifest para una cámara y un día específico.

    mac_camara: MAC Hanwha o UUID Marshall
    fecha_iso : "YYYY-MM-DD"
    """

    fecha = datetime.datetime.fromisoformat(fecha_iso).date()
    yyyy = fecha.strftime("%Y")
    mm = fecha.strftime("%m")
    dd = fecha.strftime("%d")

    # Ruta real en el grabador Hanwha/Marshall
    ruta_frag = os.path.join(
        SMB_ROOT,
        GRABADOR_UUID,
        QUALITY_FOLDER,
        mac_camara,
        yyyy,
        mm,
        dd
    )

    if not os.path.isdir(ruta_frag):
        print(f"No existe carpeta de fragmentos: {ruta_frag}")
        return False

    path_manifest = calcular_ruta_manifest(mac_camara, fecha)
    manifest = cargar_manifest(path_manifest)

    if "uuid" not in manifest:
        manifest["uuid"] = GRABADOR_UUID
    if "fecha" not in manifest:
        manifest["fecha"] = fecha_iso
    if "camara_mac" not in manifest:
        manifest["camara_mac"] = mac_camara
    if "archivos" not in manifest:
        manifest["archivos"] = []

    # Construir set de nombres ya registrados
    ya_registrados = {a["archivo"] for a in manifest["archivos"]}

    # Buscar nuevos fragmentos MKV en todas las carpetas hora (00–23)
    nuevos = []

    for root, dirs, files in os.walk(ruta_frag):
        for nombre in sorted(files):
            if not nombre.endswith(".mkv"):
                continue

            if nombre in ya_registrados:
                continue

            file_path = os.path.join(root, nombre)

            HH, MM = extraer_timestamp(nombre)
            if HH is None:
                continue

            # Crear timestamp real (fecha + hora encontrada)
            inicio = datetime.datetime(
                int(yyyy), int(mm), int(dd),
                HH, MM
            )
            fin = inicio + datetime.timedelta(minutes=1)

            entry = {
                "archivo": nombre,
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat(),
                "duracion_segundos": (fin - inicio).seconds,
                "ruta_relativa": os.path.relpath(file_path, SMB_ROOT).replace("\\", "/")
            }

            nuevos.append(entry)
            manifest["archivos"].append(entry)

    if nuevos:
        guardar_manifest(path_manifest, manifest)
        print(f"Manifest actualizado: {path_manifest}")
    else:
        print(f"Manifest sin cambios: {path_manifest}")

    return True
