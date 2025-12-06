# ============================================================
#   SEMEFO — task.py (PRODUCTION FINAL 2025)
#   Unión de fragmentos con validación estricta, pausas reales,
#   ffmpeg robusto, trazabilidad completa y API Opción B.
# ============================================================

from .celery_app import celery_app
import subprocess
import os
import shutil
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

from worker.job_api_client import (
    registrar_job,
    actualizar_job,
    registrar_archivo,
    finalizar_archivo
)

from worker.db_utils import (
    ensure_dir,
    limpiar_temp,
    normalizar_ruta
)

load_dotenv()

# ============================================================
#   CONFIG GLOBAL
# ============================================================

API_URL = os.getenv("API_SERVER_URL").rstrip("/")
PAUSA_MINIMA = 5

# RUTA REAL del storage compartido ↓↓↓↓↓
EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH", "/mnt/wave/archivos_sistema_semefo"
).rstrip("/")

TEMP_ROOT = os.getenv("TEMP_ROOT", "/opt/semefo/storage/tmp")
FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", 4))
MODO_PRUEBA = os.getenv("MODO_PRUEBA_VIDEO", "0") == "1"

os.makedirs(TEMP_ROOT, exist_ok=True)


# ============================================================
#   REPORTAR PROGRESO (solo log)
# ============================================================

def reportar_progreso(id_sesion: str, tipo_archivo: str, progreso: float):
    print(f"[PROGRESO] {tipo_archivo} sesión {id_sesion}: {progreso}%")


# ============================================================
#   UTILIDADES
# ============================================================

def cargar_manifest(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe manifest: {path}")

    with open(path, "r") as f:
        data = json.load(f)

    if "archivos" not in data:
        raise Exception("Manifest corrupto: falta 'archivos'")

    data["archivos"].sort(key=lambda x: x["inicio"])
    return data


def ffmpeg_concat_cmd(list_txt, salida):
    base = (
        f"ffmpeg -y -f concat -safe 0 -i \"{list_txt}\" "
        f"-c:v libvpx-vp9 -pix_fmt yuv420p -threads {FFMPEG_THREADS} "
    )

    if MODO_PRUEBA:
        return base + "-b:v 1.5M -crf 35 -cpu-used 6 \"" + salida + "\""

    return base + "-b:v 3M -crf 28 -cpu-used 4 \"" + salida + "\""


def detectar_pausas(frags):
    pausas = []
    for i in range(1, len(frags)):
        prev = frags[i - 1]["_dt_fin"]
        cur = frags[i]["_dt_ini"]
        gap = (cur - prev).total_seconds()

        if gap >= PAUSA_MINIMA:
            pausas.append({
                "inicio": prev.isoformat(),
                "fin": cur.isoformat(),
                "duracion": gap,
                "fragmento_anterior": frags[i - 1]["archivo"],
                "fragmento_siguiente": frags[i]["archivo"]
            })
    return pausas


def reportar_pausas_api(id_sesion, pausas):
    if not pausas:
        print("[PAUSAS] Ninguna pausa detectada")
        return

    try:
        url = f"http://{API_URL}/sesiones/{id_sesion}/pausas_detectadas"
        r = requests.post(url, json={"pausas": pausas}, timeout=5)
        print(f"[PAUSAS] Enviadas {len(pausas)} (status={r.status_code})")
    except Exception as e:
        print(f"[PAUSAS] ERROR: {e}")


def construir_lista_fragmentos(manifest, inicio, fin):
    frags = []
    for f in manifest["archivos"]:
        try:
            dt_ini = datetime.fromisoformat(f["inicio"])
            dt_fin = datetime.fromisoformat(f["fin"])
        except:
            continue

        if dt_fin >= inicio and dt_ini <= fin:
            f["_dt_ini"] = dt_ini
            f["_dt_fin"] = dt_fin
            frags.append(f)

    if not frags:
        raise Exception("Manifest vacío en rango de tiempo")

    frags.sort(key=lambda x: x["_dt_ini"])
    return frags


# ============================================================
#   UNIFICADO: UNIR VIDEO / VIDEO2
# ============================================================

def _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, tipo):

    inicio_sesion = datetime.fromisoformat(inicio_sesion)
    fin_sesion = datetime.fromisoformat(fin_sesion)

    temp_dir = os.path.join(TEMP_ROOT, f"{tipo}_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    nombre_final = "video.webm" if tipo == "video" else "video2.webm"

    # ------------------------------------------------------------
    # CREAR JOB
    # ------------------------------------------------------------
    job_id = registrar_job(str(expediente), str(id_sesion), tipo, nombre_final)
    print(f"[JOB] Iniciado job {job_id} ({tipo})")

    try:
        manifest = cargar_manifest(manifest_path)
        frags = construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion)

        # Pausas detectadas
        pausas = detectar_pausas(frags)
        reportar_pausas_api(id_sesion, pausas)

        lista_local = []

        # ------------------------------------------------------------
        # PROGRESO: COPIA FRAGMENTOS
        # ------------------------------------------------------------
        total = len(frags)
        for idx, frag in enumerate(frags, start=1):

            progreso = round((idx / total) * 100, 2)
            reportar_progreso(id_sesion, tipo, progreso)

            src = frag["ruta"]
            if not os.path.exists(src):
                raise Exception(f"Fragmento no existe: {src}")

            dst = os.path.join(temp_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            lista_local.append(dst)

        # Construir list.txt
        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for p in lista_local:
                f.write(f"file '{p}'\n")

        # ------------------------------------------------------------
        # FFMPEG - GENERAR SALIDA FINAL
        # ------------------------------------------------------------
        salida = f"{EXPEDIENTES_PATH}/{expediente}/{id_sesion}/{nombre_final}"
        ensure_dir(os.path.dirname(salida))

        cmd = ffmpeg_concat_cmd(list_txt, salida)

        print("\n========== FFMPEG CMD ==========")
        print(cmd)
        print("================================\n")

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg falló:\n{result.stderr}")

        # Validación de tamaño
        if not os.path.exists(salida) or os.path.getsize(salida) < 200_000:
            raise Exception("Archivo generado vacío o incompleto")

        # ------------------------------------------------------------
        # REGISTRAR ARCHIVO EN API
        # ------------------------------------------------------------
        registrar_archivo(
            id_sesion=str(id_sesion),
            tipo_archivo=tipo,
            ruta_convertida=normalizar_ruta(salida),
            ruta_original=normalizar_ruta(salida),
            estado="procesando"
        )

        # ------------------------------------------------------------
        # MARCAR COMO COMPLETADO
        # ------------------------------------------------------------
        finalizar_archivo(
            sesion_id=str(id_sesion),
            tipo_archivo=tipo,
            ruta=normalizar_ruta(salida)
        )

        actualizar_job(job_id, estado="completado")
        print(f"[JOB] Unión {tipo} FINALIZADA")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERROR unir {tipo}: {error_msg}")
        actualizar_job(job_id, estado="error", error=error_msg)
        return False

    finally:
        limpiar_temp(temp_dir)

    return True


# ============================================================
#   TAREAS CELERY
# ============================================================

@celery_app.task(name="worker.tasks.unir_video")
def unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video")


@celery_app.task(name="worker.tasks.unir_video2")
def unir_video2(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video2")
