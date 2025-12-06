# ============================================================
#   SEMEFO — task.py (PRODUCTION HARDENED 2025 - FIXED)
#   Unión de fragmentos con validación estricta, pausas reales,
#   trazabilidad total, ffmpeg robusto y auditoría completa.
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
PAUSA_MINIMA = 5  # segundos reales

SMB_ROOT = os.getenv("SMB_MOUNT", "/mnt/wave").rstrip("/")
TEMP_ROOT = os.getenv("TEMP_ROOT", "/opt/semefo/storage/tmp")
FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", 4))
MODO_PRUEBA = os.getenv("MODO_PRUEBA_VIDEO", "0") == "1"

os.makedirs(TEMP_ROOT, exist_ok=True)


# ============================================================
#   UTILIDADES
# ============================================================

def cargar_manifest(manifest_path):
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"No existe manifest: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if "archivos" not in manifest or not isinstance(manifest["archivos"], list):
        raise Exception("Manifest mal formado: no contiene 'archivos'.")

    manifest["archivos"].sort(key=lambda x: x["inicio"])
    return manifest


def ffmpeg_concat_cmd(lista_txt, salida_webm):
    base = (
        f"ffmpeg -y -f concat -safe 0 -i \"{lista_txt}\" "
        f"-c:v libvpx-vp9 -pix_fmt yuv420p -threads {FFMPEG_THREADS} "
    )
    if MODO_PRUEBA:
        return base + "-b:v 1.5M -crf 35 -cpu-used 6 \"" + salida_webm + "\""
    return base + "-b:v 3M -crf 28 -cpu-used 4 \"" + salida_webm + "\""


def detectar_pausas(frags):
    pausas = []
    for i in range(1, len(frags)):
        prev = frags[i - 1]["_dt_fin"]
        curr = frags[i]["_dt_ini"]
        gap = (curr - prev).total_seconds()

        if gap >= PAUSA_MINIMA:
            pausas.append({
                "inicio": prev.isoformat(),
                "fin": curr.isoformat(),
                "duracion": gap,
                "fragmento_anterior": frags[i - 1]["archivo"],
                "fragmento_siguiente": frags[i]["archivo"]
            })
    return pausas


def reportar_pausas_api(id_sesion, pausas):
    if not pausas:
        print("[PAUSAS] No hay pausas detectadas.")
        return
    try:
        url = f"http://{API_URL}/sesiones/{id_sesion}/pausas_detectadas"
        r = requests.post(url, json={"pausas": pausas}, timeout=5)
        print(
            f"[PAUSAS] Enviadas {len(pausas)} pausas (status={r.status_code})")
    except Exception as e:
        print(f"[PAUSAS] ERROR enviando pausas: {e}")


def construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion):
    seleccionados = []

    for frag in manifest["archivos"]:
        try:
            f_ini = datetime.fromisoformat(frag["inicio"])
            f_fin = datetime.fromisoformat(frag["fin"])
        except:
            print(f"[MANIFEST] Fragmento con fecha inválida: {frag}")
            continue

        if f_fin >= inicio_sesion and f_ini <= fin_sesion:
            frag["_dt_ini"] = f_ini
            frag["_dt_fin"] = f_fin
            seleccionados.append(frag)

    if not seleccionados:
        raise Exception("No hay fragmentos en el rango de sesión.")

    seleccionados.sort(key=lambda x: x["_dt_ini"])
    print(f"[UNION] Fragmentos seleccionados: {len(seleccionados)}")
    return seleccionados


# ============================================================
#   UNIÓN DE VIDEO (INTERNA)
# ============================================================

def _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, tipo):

    inicio_sesion = datetime.fromisoformat(inicio_sesion) if isinstance(
        inicio_sesion, str) else inicio_sesion
    fin_sesion = datetime.fromisoformat(
        fin_sesion) if isinstance(fin_sesion, str) else fin_sesion

    temp_dir = os.path.join(TEMP_ROOT, f"{tipo}_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    expediente = str(expediente)
    id_sesion = str(id_sesion)
    nombre_final = "video.webm" if tipo == "video" else "video2.webm"

    job_id = registrar_job(expediente, id_sesion, tipo, nombre_final)
    print(f"[JOB] Iniciando job {job_id} para unir {tipo}")

    try:
        manifest = cargar_manifest(manifest_path)
        frags = construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion)

        pausas_detectadas = detectar_pausas(frags)
        reportar_pausas_api(id_sesion, pausas_detectadas)

        lista_local = []
        for frag in frags:
            src = frag["ruta"]
            if not os.path.exists(src):
                raise Exception(f"Fragmento no existe: {src}")
            if os.path.getsize(src) < 50_000:
                raise Exception(f"Fragmento sospechosamente pequeño: {src}")

            dst = os.path.join(temp_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            lista_local.append(dst)

        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for p in lista_local:
                f.write(f"file '{p}'\n")

        carpeta = f"{SMB_ROOT}/archivos_sistema_semefo/{expediente}/{id_sesion}"
        ensure_dir(carpeta)

        salida = f"{carpeta}/{nombre_final}"
        cmd = ffmpeg_concat_cmd(list_txt, salida)

        print("\n========== FFMPEG CMD ==========")
        print(cmd)
        print("================================\n")

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise Exception(f"FFmpeg falló: {result.stderr}")

        if not os.path.exists(salida) or os.path.getsize(salida) < 200_000:
            raise Exception(f"{nombre_final} generado vacío o incompleto.")

        # 🔥 Registro correcto con firma REAL
        registrar_archivo(
            id_sesion=id_sesion,
            tipo_archivo=tipo,
            ruta_convertida=normalizar_ruta(salida),
            ruta_original=normalizar_ruta(manifest_path)
        )

        finalizar_archivo(id_sesion, tipo, normalizar_ruta(salida))
        actualizar_job(job_id, estado="completado")

        print(f"[JOB] Unión de {tipo} completada OK.")
        return True

    except Exception as e:
        print(f"\n❌ ERROR unir_{tipo}: {e}\n")
        actualizar_job(job_id, estado="error", error=str(e))
        return False

    finally:
        limpiar_temp(temp_dir)


# ============================================================
#   TAREAS CELERY PÚBLICAS (FIX: no fallan si llega un arg extra)
# ============================================================

@celery_app.task(name="worker.tasks.unir_video")
def unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video")


@celery_app.task(name="worker.tasks.unir_video2")
def unir_video2(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video2")
