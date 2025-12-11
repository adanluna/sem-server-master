# ============================================================
#   SEMEFO — task.py
#   Recorte y unión final SIN start_time real (solo segundos)
#   PRODUCCIÓN FINAL 2025
# ============================================================

from .celery_app import celery_app
import subprocess
import os
import shutil
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

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
MODO_PRUEBA = os.getenv("MODO_PRUEBA_VIDEO", "0") == "1"

os.makedirs(TEMP_ROOT, exist_ok=True)

# ============================================================
#   UTILIDADES
# ============================================================


def cargar_manifest(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe manifest: {path}")
    with open(path, "r") as f:
        data = json.load(f)
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


def obtener_pausas_api(id_sesion):
    try:
        r = requests.get(
            f"{API_URL}/sesiones/{id_sesion}/pausas_todas", timeout=5)
        return r.json().get("pausas", [])
    except:
        return []


def construir_intervalos_validos(inicio_sesion, fin_sesion, pausas):
    pausas_ordenadas = sorted(pausas, key=lambda x: x["inicio"])
    intervalos = []
    cursor = inicio_sesion

    for p in pausas_ordenadas:
        p_ini = datetime.fromisoformat(p["inicio"])
        p_fin = datetime.fromisoformat(p["fin"])

        if p_ini > cursor:
            intervalos.append({"ini": cursor, "fin": p_ini})

        cursor = max(cursor, p_fin)

    if cursor < fin_sesion:
        intervalos.append({"ini": cursor, "fin": fin_sesion})

    return intervalos


def fragmentos_del_manifest(manifest, inicio, fin):
    frags = []
    for f in manifest["archivos"]:
        dt_ini = datetime.fromisoformat(f["inicio"])
        dt_fin = datetime.fromisoformat(f["fin"])

        if dt_fin >= inicio and dt_ini <= fin:
            f["_dt_ini"] = dt_ini
            f["_dt_fin"] = dt_fin
            frags.append(f)

    frags.sort(key=lambda x: x["_dt_ini"])
    return frags


def recortar_fragmento(src, inicio_seg, fin_seg, dst):
    duracion = fin_seg - inicio_seg
    if duracion <= 0:
        raise Exception("Duración inválida al recortar")

    cmd = (
        f"ffmpeg -y "
        f"-ss {inicio_seg} -i \"{src}\" "
        f"-t {duracion} "
        f"-c:v libvpx-vp9 -pix_fmt yuv420p "
        f"-threads {FFMPEG_THREADS} -b:v 3M -crf 28 -cpu-used 4 "
        f"\"{dst}\""
    )

    print(f"[FFMPEG TRIM] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Trim falló:\n{result.stderr}")

    if not os.path.exists(dst) or os.path.getsize(dst) < 80_000:
        raise Exception("Fragmento recortado vacío o demasiado pequeño")

# ============================================================
#   UNIFICADO: unir_video / unir_video2
# ============================================================


def _unir_video(expediente, id_sesion, manifest_path, _inicio, _fin, tipo):

    # === 1. Obtener datos reales desde la API (inicio, fin, pausas) ===
    data = requests.get(
        f"{API_URL}/sesiones/{id_sesion}/pausas_todas", timeout=5).json()

    inicio_sesion = datetime.fromisoformat(data["inicio_sesion"])
    fin_sesion = datetime.fromisoformat(data["fin_sesion"])
    pausas = data.get("pausas", [])

    print(f"[SESION] Inicio oficial: {inicio_sesion}")
    print(f"[SESION] Fin oficial:   {fin_sesion}")
    print(f"[PAUSAS] Recibidas:     {len(pausas)}")

    # === 2. Preparar carpeta temporal ===
    temp_dir = os.path.join(TEMP_ROOT, f"{tipo}_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    nombre_final = "video.webm" if tipo == "video" else "video2.webm"

    # === 3. Registrar job ===
    job_id = registrar_job(str(expediente), str(id_sesion), tipo, nombre_final)

    try:
        # === 4. Cargar manifest ===
        manifest = cargar_manifest(manifest_path)
        frags = fragmentos_del_manifest(manifest, inicio_sesion, fin_sesion)

        # === 5. Construir intervalos sin pausas ===
        intervalos = construir_intervalos_validos(
            inicio_sesion, fin_sesion, pausas)
        print(f"[INTERVALOS] {len(intervalos)} intervalos válidos detectados")

        lista_local = []
        part_idx = 0

        # === 6. Procesar intervalos ===
        for intervalo in intervalos:
            int_ini = intervalo["ini"]
            int_fin = intervalo["fin"]

            for frag in frags:
                dt_ini = frag["_dt_ini"]
                dt_fin = frag["_dt_fin"]

                # solapamiento
                if dt_fin <= int_ini or dt_ini >= int_fin:
                    continue

                src = frag["ruta"]

                # Tiempo relativo SIN start_time real
                ini_seg = max(0, (int_ini - dt_ini).total_seconds())
                fin_seg = min((int_fin - dt_ini).total_seconds(),
                              (dt_fin - dt_ini).total_seconds())

                if fin_seg <= ini_seg:
                    continue

                part_idx += 1
                dst = os.path.join(temp_dir, f"part_{part_idx}.mkv")

                print(f"[TRIM] {src} -> {dst}  {ini_seg}–{fin_seg}")
                recortar_fragmento(src, ini_seg, fin_seg, dst)
                lista_local.append(dst)

        if not lista_local:
            raise Exception("No se generaron fragmentos válidos")

        # === 7. Crear list.txt ===
        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for p in lista_local:
                f.write(f"file '{p}'\n")

        # === 8. Generar archivo final ===
        salida = f"{EXPEDIENTES_PATH}/{expediente}/{id_sesion}/{nombre_final}"
        ensure_dir(os.path.dirname(salida))

        cmd = ffmpeg_concat_cmd(list_txt, salida)
        print("\n========== FFMPEG CONCAT ==========")
        print(cmd)
        print("===================================\n")

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Concat falló:\n{result.stderr}")

        # === 9. Registrar archivo en API ===
        registrar_archivo(
            id_sesion=str(id_sesion),
            tipo_archivo=tipo,
            ruta_convertida=normalizar_ruta(salida),
            ruta_original=normalizar_ruta(salida),
            estado="procesando"
        )

        # Actualizar estado en API
        requests.put(
            f"{API_URL}/archivos/{id_sesion}/{tipo}/actualizar_estado",
            json={
                "estado": "completado",
                "ruta_convertida": normalizar_ruta(salida),
                "conversion_completa": True
            },
            timeout=5
        )

        actualizar_job(job_id, estado="completado")
        print(f"[JOB] Unión {tipo} FINALIZADA")

        # enviar a whisper solo para el video principal
        if tipo == "video":
            try:
                requests.post(
                    f"{API_URL}/whisper/enviar",
                    json={"expediente": expediente, "sesion_id": id_sesion},
                    timeout=5
                )
            except:
                pass

    except Exception as e:
        actualizar_job(job_id, estado="error", error=str(e))
        print(f"❌ ERROR unir {tipo}: {e}")
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
