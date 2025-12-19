# ============================================================
#   SEMEFO — task.py
#   Recorte por intervalos válidos (manual + manifest)
#   Unión final sin pausas — PRODUCCIÓN FINAL 2025
# ============================================================

from .celery_app import celery_app
import subprocess
import os
import shutil
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
PAUSA_MINIMA = 5

EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH", "/mnt/wave/archivos_sistema_semefo").rstrip("/")
TEMP_ROOT = os.getenv("TEMP_ROOT", "/opt/semefo/storage/tmp")
FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", 4))
ENCODER = os.getenv("VIDEO_ENCODER", "cpu").lower()

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
        f"-vf \"scale=1920:1080,fps=30\" "
        f"-c:v libvpx-vp9 "
        f"-b:v 0 -crf 34 "
        f"-row-mt 1 "
        f"-threads 4 "
        f"-pix_fmt yuv420p "
        f"-c:a libopus -ac 1 -ar 16000 "
        f"-reset_timestamps 1 "
        f"\"{salida}\""
    )


def obtener_pausas_api(id_sesion):
    url = f"{API_URL}/sesiones/{id_sesion}/pausas_todas"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        return data.get("pausas", [])
    except Exception as e:
        print(f"[PAUSAS] ERROR obteniendo pausas API: {e}")
        return []


def construir_intervalos_validos(inicio_sesion, fin_sesion, pausas):
    """
    A partir de [inicio_sesion, fin_sesion] y una lista de pausas,
    genera intervalos válidos (sin pausas).
    """
    pausas_ordenadas = sorted(pausas, key=lambda x: x["inicio"])
    intervalos = []
    cursor = inicio_sesion

    for p in pausas_ordenadas:
        p_ini = datetime.fromisoformat(p["inicio"])
        p_fin = datetime.fromisoformat(p["fin"])

        if p_fin <= cursor:
            continue

        if p_ini > cursor:
            intervalos.append({"ini": cursor, "fin": p_ini})

        cursor = max(cursor, p_fin)

    if cursor < fin_sesion:
        intervalos.append({"ini": cursor, "fin": fin_sesion})

    return intervalos


def fragmentos_del_manifest(manifest, inicio, fin):
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
        raise Exception("Manifest vacío o sin fragmentos en rango")

    frags.sort(key=lambda x: x["_dt_ini"])
    return frags


def recortar_fragmento(src, inicio_seg, fin_seg, dst):
    duracion = fin_seg - inicio_seg
    if duracion <= 0:
        raise Exception("Duración inválida")


def recortar_fragmento(src, inicio_seg, fin_seg, dst):
    duracion = fin_seg - inicio_seg
    if duracion <= 0:
        raise Exception("Duración inválida")

    cmd = (
        f"ffmpeg -y "
        f"-ss {inicio_seg} "
        f"-i \"{src}\" "
        f"-t {duracion} "
        f"-map 0:v:0 -map 0:a? "
        f"-c copy "
        f"\"{dst}\""
    )

    print(f"[FFMPEG TRIM] {cmd}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(result.stderr)

    # Archivo válido mínimo (80KB aprox)
    if not os.path.exists(dst) or os.path.getsize(dst) < 80_000:
        raise Exception("Archivo recortado vacío o demasiado pequeño")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)


# ============================================================
#   UNIFICADO: UNIR VIDEO / VIDEO2 (CON RECORTES)
# ============================================================

def _unir_video(expediente, id_sesion, manifest_path, inicio_sesion_iso, fin_sesion_iso, tipo):

    info_url = f"{API_URL}/sesiones/{id_sesion}/pausas_todas"

    try:
        info = requests.get(info_url, timeout=5).json()

        inicio_sesion_iso = info.get("inicio_sesion")
        fin_sesion_iso = info.get("fin_sesion")
        pausas = info.get("pausas", [])

        if not inicio_sesion_iso or not fin_sesion_iso:
            raise Exception(
                "API no envió inicio_sesion o fin_sesion — No se puede unir el video")

        inicio_sesion = datetime.fromisoformat(inicio_sesion_iso)
        fin_sesion = datetime.fromisoformat(fin_sesion_iso)

    except Exception as e:
        raise Exception(f"Error obteniendo datos de sesión desde API: {e}")

    print(f"[SESION] Inicio oficial: {inicio_sesion}")
    print(f"[SESION] Fin oficial:   {fin_sesion}")
    print(f"[PAUSAS] Recibidas:     {len(pausas)}")

    temp_dir = os.path.join(TEMP_ROOT, f"{tipo}_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    nombre_final = "video.webm" if tipo == "video" else "video2.webm"

    # Crear job
    job_id = registrar_job(str(expediente), str(id_sesion), tipo, nombre_final)
    print(f"[JOB] Iniciado job {job_id} ({tipo})")

    try:
        # Manifest
        manifest = cargar_manifest(manifest_path)
        frags = fragmentos_del_manifest(manifest, inicio_sesion, fin_sesion)

        # Pausas (manuales + auto)
        pausas = obtener_pausas_api(id_sesion)
        print(f"[PAUSAS] Total recibidas: {len(pausas)}")

        # Intervalos válidos (sin pausas)
        intervalos = construir_intervalos_validos(
            inicio_sesion, fin_sesion, pausas)
        print(f"[INTERVALOS] {len(intervalos)} intervalos válidos detectados")

        lista_local = []
        part_idx = 0

        # Para cada intervalo válido...
        for intervalo in intervalos:
            int_ini = intervalo["ini"]
            int_fin = intervalo["fin"]

            for frag in frags:
                dt_ini = frag["_dt_ini"]
                dt_fin = frag["_dt_fin"]
                src = frag["ruta"]

                # Checar solapamiento
                if dt_fin <= int_ini or dt_ini >= int_fin:
                    continue

                # Tiempos relativos dentro del fragmento
                ini_seg = max(0, (int_ini - dt_ini).total_seconds())
                fin_seg = min((dt_fin - dt_ini).total_seconds(),
                              (int_fin - dt_ini).total_seconds())

                if fin_seg <= ini_seg:
                    continue

                part_idx += 1
                dst = os.path.join(temp_dir, f"part_{part_idx}.mkv")

                print(f"[TRIM] {src} -> {dst}  {ini_seg}–{fin_seg}")

                recortar_fragmento(src, ini_seg, fin_seg, dst)
                lista_local.append(dst)

        if not lista_local:
            raise Exception(
                "No se generaron fragmentos válidos tras recorte por pausas")

        # Crear list.txt
        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for p in lista_local:
                f.write(f"file '{p}'\n")

        # Salida final
        salida = f"{EXPEDIENTES_PATH}/{expediente}/{id_sesion}/{nombre_final}"
        ensure_dir(os.path.dirname(salida))

        print("⏳ Verificando carga de CPU antes de FFmpeg final...")
        esperar_cpu_baja(limite=85)

        cmd = ffmpeg_concat_cmd(list_txt, salida)
        print("\n========== FFMPEG CONCAT ==========")
        print(cmd)
        print("===================================\n")

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Concat falló:\n{result.stderr}")

        if not os.path.exists(salida) or os.path.getsize(salida) < 200_000:
            raise Exception("Archivo final vacío")

        # Registrar archivo en API
        registrar_archivo(
            id_sesion=str(id_sesion),
            tipo_archivo=tipo,
            ruta_convertida=normalizar_ruta(salida),
            ruta_original=normalizar_ruta(salida),
            estado="procesando"
        )

        # Actualizar estado
        url = f"{API_URL}/archivos/{id_sesion}/{tipo}/actualizar_estado"
        payload = {
            "estado": "completado",
            "ruta_convertida": normalizar_ruta(salida),
            "conversion_completa": True,
            "mensaje": f"Archivo finalizado correctamente"
        }
        requests.put(url, json=payload, timeout=5)

        actualizar_job(job_id, estado="completado")
        print(f"[JOB] Unión {tipo} FINALIZADA")

        # Enviar a Whisper solo para el video principal
        if tipo == "video":
            try:
                payload = {"expediente": expediente, "sesion_id": id_sesion}
                requests.post(f"{API_URL}/whisper/enviar",
                              json=payload, timeout=5)
            except Exception as e:
                print(f"[WHISPER] ERROR: {e}")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERROR unir {tipo}: {error_msg}")
        actualizar_job(job_id, estado="error", error=error_msg)
        return False

    finally:
        limpiar_temp(temp_dir)

    return True


def esperar_cpu_baja(limite=85, intervalo=5):
    """
    Espera activa hasta que el uso de CPU baje del límite.
    Evita saturación del servidor.
    """
    while True:
        cpu = psutil.cpu_percent(interval=1)
        if cpu < limite:
            return
        print(f"⚠️ CPU alta ({cpu}%), esperando {intervalo}s...")
        time.sleep(intervalo)


# ============================================================
#   TAREAS CELERY
# ============================================================

@celery_app.task(name="worker.tasks.unir_video")
def unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video")


@celery_app.task(name="worker.tasks.unir_video2")
def unir_video2(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video2")
