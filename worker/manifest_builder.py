# ============================================================
#   SEMEFO — manifest_builder.py (PRODUCTION HARDENED 2025)
#   Generación incremental segura de manifest con validaciones
#   estrictas, prevención de corrupción y auditoría extendida.
#   Compatible 100% con tasks.py incluida detección de pausas.
# ============================================================

import os
import json
import datetime
import subprocess
from glob import glob
from dotenv import load_dotenv
from .celery_app import celery_app
from worker.job_api_client import actualizar_job
from worker.heartbeat import send_heartbeat
from datetime import datetime, timezone

load_dotenv()

# Ruta raíz del SMB montado en el contenedor
SMB_ROOT = os.getenv("SMB_MOUNT", "/mnt/wave").rstrip("/")
GRABADOR_UUID = os.getenv("GRABADOR_UUID", "UNKNOWN_UUID")

EXT_FRAGMENTO = "*.mkv"


# ============================================================
#   UTILIDADES
# ============================================================

def obtener_duracion(path):
    """Obtiene duración REAL del MKV usando ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-show_entries",
                "format=duration", "-of", "csv=p=0", path
            ],
            capture_output=True,
            text=True
        )

        if not result.stdout.strip():
            print(f"[MANIFEST] ffprobe sin output → archivo corrupto: {path}")
            return None

        dur = float(result.stdout.strip())

        if dur <= 0:
            print(f"[MANIFEST] Duración inválida (<=0) para {path}")
            return None

        return dur

    except Exception as e:
        print(f"[MANIFEST] Error obteniendo duración para {path}: {e}")
        return None


def extraer_timestamps(filename, fullpath):
    """
    Convierte nombres como:
      - 1764662554731_76000.mkv  (fragmento completo)
      - 1764662554731.mkv        (fragmento incompleto → ignorar)
    """

    if "_" not in filename:
        print(
            f"[MANIFEST] Ignorando fragmento incompleto (sin sufijo): {filename}")
        return None, None, None

    try:
        base = filename.split("_")[0]  # ej: 1764662554731
        ts_ms = int(base)

        # Conversión segura a datetime
        inicio = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

        dur = obtener_duracion(fullpath)
        if dur is None:
            return None, None, None

        fin = inicio + datetime.timedelta(seconds=dur)
        return inicio, fin, dur

    except ValueError:
        print(f"[MANIFEST] Nombre inválido (timestamp corrupto): {filename}")
        return None, None, None
    except Exception as e:
        print(f"[MANIFEST] Error procesando timestamp para {filename}: {e}")
        return None, None, None


def cargar_manifest(path_manifest):
    if os.path.exists(path_manifest):
        try:
            with open(path_manifest, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "archivos" not in data:
                    print(
                        f"[MANIFEST] Archivo corrupto → se repara vacío: {path_manifest}")
                    return {}
                return data
        except Exception as e:
            print(f"[MANIFEST] Error leyendo manifest {path_manifest}: {e}")
            return {}
    return {}


def guardar_manifest(path_manifest, data):
    os.makedirs(os.path.dirname(path_manifest), exist_ok=True)

    try:
        with open(path_manifest, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[MANIFEST] ERROR guardando manifest {path_manifest}: {e}")


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
        mm,
        dd,
        "manifest.json"
    )


# ============================================================
#   CELERY TASK — GENERAR MANIFEST INCREMENTAL SEGURo
# ============================================================

@celery_app.task(name="tasks.generar_manifest", queue="manifest")
def generar_manifest(mac_camara, fecha_iso, job_id):
    """
    Genera o actualiza el manifest de una cámara en un día.
    Solo agrega fragmentos nuevos, con validación extendida.
    Ahora espera 5 minutos ANTES de generar el manifest.
    """
    import time
    try:
        # ============================================================
        #   ESPERA REQUERIDA PARA ASEGURAR EL ÚLTIMO FRAGMENTO
        # ============================================================
        # por defecto 5 minutos
        WAIT_SECONDS = int(os.getenv("MANIFEST_WAIT_SECONDS", "300"))

        print(
            f"[MANIFEST] Esperando {WAIT_SECONDS} segundos antes de generar manifest para cámara {mac_camara}...")
        time.sleep(WAIT_SECONDS)
        print(
            f"[MANIFEST] Iniciando generación real del manifest para cámara {mac_camara}")

        pid = os.getpid()

        actualizar_job(job_id, estado="en_progreso", error=None)

        # send_heartbeat(
        #    worker="manifest",
        #    status="processing",
        #    pid=pid,
        #    queue="manifest"
        # )

        fecha_base = datetime.fromisoformat(fecha_iso).date()
        fechas_a_procesar = obtener_fechas_a_procesar(fecha_base)

        todas_las_rutas = []

        for fecha in fechas_a_procesar:
            ruta_frag = os.path.join(
                SMB_ROOT,
                GRABADOR_UUID,
                "hi_quality",
                mac_camara,
                fecha.strftime("%Y"),
                fecha.strftime("%m"),
                fecha.strftime("%d")
            )

            pattern = os.path.join(ruta_frag, "*", EXT_FRAGMENTO)
            todas_las_rutas.extend(glob(pattern))

        if not todas_las_rutas:
            msg = "No se encontraron fragmentos para generar manifest"
            actualizar_job(job_id, estado="error", error=msg)
            raise RuntimeError(msg)

        fragmentos = sorted(todas_las_rutas)

        path_manifest = ruta_manifest(mac_camara, fecha_base)
        manifest = cargar_manifest(path_manifest)

        manifest.setdefault("uuid", GRABADOR_UUID)
        manifest.setdefault("fecha", fecha_iso)
        manifest.setdefault("camara_mac", mac_camara)
        manifest.setdefault("archivos", [])

        ya_archivos = {a["archivo"] for a in manifest["archivos"]}
        ya_timestamps = {(a["inicio"], a["fin"]) for a in manifest["archivos"]}

        nuevos = []

        for file_path in fragmentos:
            archivo = os.path.basename(file_path)

            if archivo in ya_archivos:
                continue

            inicio, fin, dur = extraer_timestamps(archivo, file_path)
            if inicio is None:
                continue

            if (inicio.isoformat(), fin.isoformat()) in ya_timestamps:
                print(f"[MANIFEST] Duplicado por timestamp evitado: {archivo}")
                continue

            entry = {
                "archivo": archivo,
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat(),
                "duracion_segundos": dur,
                "ruta": file_path
            }

            manifest["archivos"].append(entry)
            nuevos.append(entry)

        manifest["archivos"].sort(key=lambda x: x["inicio"])

        guardar_manifest(path_manifest, manifest)

        print(f"[MANIFEST] Guardado → {path_manifest}")
        print(f"[MANIFEST] Fragmentos nuevos agregados: {len(nuevos)}")

        actualizar_job(
            job_id,
            estado="completado",
            resultado="Manifest generado correctamente"
        )

        return True

    except Exception as e:
        actualizar_job(
            job_id,
            estado="error",
            error=str(e)
        )
        raise
    # finally:
    #    send_heartbeat(
    #        worker="manifest",
    #        status="listening",
    #        pid=pid,
    #        queue="manifest"
    #    )


def obtener_fechas_a_procesar(fecha_base):
    """
    Retorna lista de fechas a procesar.
    Soporta cruce de día (23:59 → 00:01).
    """
    return [
        fecha_base,
        fecha_base + datetime.timedelta(days=1)
    ]
