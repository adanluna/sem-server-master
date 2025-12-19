# ============================================================
#   SEMEFO — task.py
#   Recorte por intervalos válidos (manual + manifest)
#   Unión final sin pausas — PRODUCCIÓN FINAL 2025 (FAST)
# ============================================================

from .celery_app import celery_app
import subprocess
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import psutil
import time

from worker.job_api_client import registrar_job, actualizar_job, registrar_archivo
from worker.db_utils import ensure_dir, limpiar_temp, normalizar_ruta

load_dotenv()

# ============================================================
#   CONFIG GLOBAL
# ============================================================

API_URL = os.getenv("API_SERVER_URL").rstrip("/")
EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH", "/mnt/wave/archivos_sistema_semefo").rstrip("/")
TEMP_ROOT = os.getenv("TEMP_ROOT", "/opt/semefo/storage/tmp")
FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", 4))

os.makedirs(TEMP_ROOT, exist_ok=True)

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
    return (
        f"ffmpeg -y "
        f"-fflags +genpts "
        f"-f concat -safe 0 -i \"{list_txt}\" "
        f"-map 0:v:0 -map 0:a? "
        f"-vf \"scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=20\" "
        f"-c:v libvpx "
        f"-b:v 1.5M "
        f"-threads 4 "
        f"-pix_fmt yuv420p "
        f"-c:a libopus -ac 1 -ar 16000 -b:a 32k "
        f"-reset_timestamps 1 "
        f"\"{salida}\""
    )


def obtener_pausas_api(id_sesion):
    try:
        r = requests.get(
            f"{API_URL}/sesiones/{id_sesion}/pausas_todas", timeout=5)
        return r.json().get("pausas", [])
    except Exception as e:
        print(f"[PAUSAS] ERROR API: {e}")
        return []


def construir_intervalos_validos(inicio_sesion, fin_sesion, pausas):
    pausas = sorted(pausas, key=lambda x: x["inicio"])
    intervalos = []
    cursor = inicio_sesion

    for p in pausas:
        ini = datetime.fromisoformat(p["inicio"])
        fin = datetime.fromisoformat(p["fin"])

        if fin <= cursor:
            continue

        if ini > cursor:
            intervalos.append({"ini": cursor, "fin": ini})

        cursor = max(cursor, fin)

    if cursor < fin_sesion:
        intervalos.append({"ini": cursor, "fin": fin_sesion})

    return intervalos


def fragmentos_del_manifest(manifest, inicio, fin):
    frags = []
    for f in manifest["archivos"]:
        try:
            f["_dt_ini"] = datetime.fromisoformat(f["inicio"])
            f["_dt_fin"] = datetime.fromisoformat(f["fin"])
        except:
            continue

        if f["_dt_fin"] >= inicio and f["_dt_ini"] <= fin:
            frags.append(f)

    if not frags:
        raise Exception("No hay fragmentos válidos en el manifest")

    return sorted(frags, key=lambda x: x["_dt_ini"])


def recortar_fragmento(src, ini_seg, fin_seg, dst):
    duracion = fin_seg - ini_seg
    if duracion <= 0:
        raise Exception("Duración inválida")

    cmd = (
        f"ffmpeg -y "
        f"-ss {ini_seg} -i \"{src}\" "
        f"-t {duracion} "
        f"-map 0:v:0 -map 0:a? "
        f"-c copy "
        f"\"{dst}\""
    )

    print(f"[FFMPEG TRIM] {cmd}")

    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        raise Exception(r.stderr)

    if not os.path.exists(dst) or os.path.getsize(dst) < 80_000:
        raise Exception("Fragmento inválido o vacío")


def esperar_cpu_baja(limite=85):
    while True:
        cpu = psutil.cpu_percent(interval=1)
        if cpu < limite:
            return
        print(f"⚠️ CPU alta ({cpu}%), esperando...")
        time.sleep(3)

# ============================================================
#   CORE
# ============================================================


def _unir_video(expediente, id_sesion, manifest_path, tipo):

    info = requests.get(
        f"{API_URL}/sesiones/{id_sesion}/pausas_todas", timeout=5).json()

    inicio = datetime.fromisoformat(info["inicio_sesion"])
    fin = datetime.fromisoformat(info["fin_sesion"])
    pausas = info.get("pausas", [])

    print(f"[SESION] {inicio} → {fin}")
    print(f"[PAUSAS] {len(pausas)}")

    temp_dir = os.path.join(TEMP_ROOT, f"{tipo}_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    nombre_final = "video.webm" if tipo == "video" else "video2.webm"
    job_id = registrar_job(expediente, id_sesion, tipo, nombre_final)

    try:
        manifest = cargar_manifest(manifest_path)
        frags = fragmentos_del_manifest(manifest, inicio, fin)
        intervalos = construir_intervalos_validos(inicio, fin, pausas)

        partes = []
        idx = 0

        for intervalo in intervalos:
            for f in frags:
                if f["_dt_fin"] <= intervalo["ini"] or f["_dt_ini"] >= intervalo["fin"]:
                    continue

                ini = max(0, (intervalo["ini"] - f["_dt_ini"]).total_seconds())
                fin_ = min(
                    (intervalo["fin"] - f["_dt_ini"]).total_seconds(),
                    (f["_dt_fin"] - f["_dt_ini"]).total_seconds()
                )

                if fin_ <= ini:
                    continue

                idx += 1
                dst = os.path.join(temp_dir, f"part_{idx}.mkv")
                recortar_fragmento(f["ruta"], ini, fin_, dst)
                partes.append(dst)

        if not partes:
            raise Exception("No se generaron fragmentos")

        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for p in partes:
                f.write(f"file '{p}'\n")

        salida = f"{EXPEDIENTES_PATH}/{expediente}/{id_sesion}/{nombre_final}"
        ensure_dir(os.path.dirname(salida))

        esperar_cpu_baja()

        cmd = ffmpeg_concat_cmd(list_txt, salida)
        print("\n========== FFMPEG CONCAT ==========")
        print(cmd)
        print("==================================")

        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            raise Exception(r.stderr)

        if not os.path.exists(salida) or os.path.getsize(salida) < 200_000:
            raise Exception("Archivo final inválido")

        registrar_archivo(
            id_sesion=str(id_sesion),
            tipo_archivo=tipo,
            ruta_convertida=normalizar_ruta(salida),
            ruta_original=normalizar_ruta(salida),
            estado="completado"
        )

        actualizar_job(job_id, estado="completado")

        if tipo == "video":
            requests.post(
                f"{API_URL}/whisper/enviar",
                json={"expediente": expediente, "sesion_id": id_sesion},
                timeout=5
            )

    except Exception as e:
        actualizar_job(job_id, estado="error", error=str(e))
        raise

    finally:
        limpiar_temp(temp_dir)

    return True

# ============================================================
#   TAREAS CELERY
# ============================================================


@celery_app.task(name="worker.tasks.unir_video")
def unir_video(expediente, id_sesion, manifest_path, *_):
    return _unir_video(expediente, id_sesion, manifest_path, "video")


@celery_app.task(name="worker.tasks.unir_video2")
def unir_video2(expediente, id_sesion, manifest_path, *_):
    return _unir_video(expediente, id_sesion, manifest_path, "video2")
