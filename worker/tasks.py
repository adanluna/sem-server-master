# ============================================================
#   SEMEFO — task.py (FINAL)
#   Master server (172.31.82.2)
#   Une fragmentos de cámara 1 y cámara 2 usando su MANIFEST
#   y genera video.webm y video2.webm en SMB.
#
#   No se guardan archivos en Linux.
# ============================================================

from .celery_app import celery_app
import subprocess
import os
import shutil
import json
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

SMB_ROOT = os.getenv("SMB_MOUNT", "/mnt/semefo").rstrip("/")
FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", 4))
MODO_PRUEBA = os.getenv("MODO_PRUEBA_VIDEO", "0") == "1"

TEMP_ROOT = "/tmp/semefo_temp"
os.makedirs(TEMP_ROOT, exist_ok=True)

GRABADOR_UUID = os.getenv("GRABADOR_UUID", "").strip()

# ============================================================
#   UTILIDADES
# ============================================================


def cargar_manifest(manifest_path):
    """
    Carga el manifest.json desde el SMB.
    """
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"No existe manifest: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ffmpeg_concat_cmd(lista_txt, salida_webm):
    """
    Genera comando FFMPEG final para unir videos.
    """
    if MODO_PRUEBA:
        return (
            f"ffmpeg -y -f concat -safe 0 -i {lista_txt} "
            f"-c:v libvpx-vp9 -b:v 1.5M -crf 35 -cpu-used 6 "
            f"-pix_fmt yuv420p -threads {FFMPEG_THREADS} {salida_webm}"
        )
    else:
        return (
            f"ffmpeg -y -f concat -safe 0 -i {lista_txt} "
            f"-c:v libvpx-vp9 -b:v 3M -crf 28 -cpu-used 4 "
            f"-pix_fmt yuv420p -threads {FFMPEG_THREADS} {salida_webm}"
        )


def construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion):
    """
    Dado un manifest con fragmentos:
        [{archivo, inicio, fin}, ...]
    Devuelve solo los fragmentos cuya intersección con la sesión es válida.
    """
    seleccionados = []

    for frag in manifest["archivos"]:
        f_ini = frag["inicio"]
        f_fin = frag["fin"]

        if f_fin >= inicio_sesion and f_ini <= fin_sesion:
            seleccionados.append(frag)

    if not seleccionados:
        raise Exception(
            "No se encontraron fragmentos que coincidan con la sesión")

    seleccionados.sort(key=lambda x: x["inicio"])
    return seleccionados


# ============================================================
#   UNIÓN DE VIDEO 1 (PRINCIPAL)
# ============================================================

@celery_app.task(name="worker.tasks.unir_video")
def unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    """
    Une fragmentos MKV de cámara 1 según MANIFEST externo.
    Guarda video.webm en SMB.
    """
    temp_dir = os.path.join(TEMP_ROOT, f"vid1_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    job_id = None

    try:
        expediente = str(expediente)
        id_sesion = str(id_sesion)

        # Registrar job
        job_id = registrar_job(expediente, id_sesion, "video", "video.webm")

        # Cargar manifest
        manifest = cargar_manifest(manifest_path)

        # Seleccionar fragmentos
        frags = construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion)

        # Copiar fragmentos a tmp
        lista_local = []
        for frag in frags:
            src = frag["ruta"]
            dst = os.path.join(temp_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            lista_local.append(dst)

        # Crear list.txt
        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for frag in lista_local:
                f.write(f"file '{frag}'\n")

        # Ruta salida
        carpeta_salida = f"{SMB_ROOT}/{expediente}/{id_sesion}"
        ensure_dir(carpeta_salida)
        salida = f"{carpeta_salida}/video.webm"

        # Ejecutar ffmpeg
        cmd = ffmpeg_concat_cmd(list_txt, salida)
        print("FFMPEG VIDEO1 CMD:", cmd)
        subprocess.run(cmd, shell=True, check=True, timeout=1800)

        # Validación
        if not os.path.exists(salida) or os.path.getsize(salida) < 1_000_000:
            raise Exception("video.webm generado con tamaño insuficiente")

        registrar_archivo(id_sesion, "video", normalizar_ruta(salida))
        finalizar_archivo(id_sesion, "video", normalizar_ruta(salida))

        actualizar_job(job_id, estado="completado",
                       resultado=normalizar_ruta(salida))
        return True

    except Exception as e:
        print("ERROR unir_video:", e)
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        return False

    finally:
        limpiar_temp(temp_dir)


# ============================================================
#   UNIÓN DE VIDEO 2 (RESPALDO)
# ============================================================

@celery_app.task(name="worker.tasks.unir_video2")
def unir_video2(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    """
    Une fragmentos MKV de cámara 2 según MANIFEST externo.
    Guarda video2.webm en SMB.
    """
    temp_dir = os.path.join(TEMP_ROOT, f"vid2_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    job_id = None

    try:
        expediente = str(expediente)
        id_sesion = str(id_sesion)

        job_id = registrar_job(expediente, id_sesion, "video2", "video2.webm")

        # Cargar manifest
        manifest = cargar_manifest(manifest_path)

        # Seleccionar fragmentos
        frags = construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion)

        lista_local = []
        for frag in frags:
            src = frag["ruta"]
            dst = os.path.join(temp_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            lista_local.append(dst)

        # list.txt
        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for frag in lista_local:
                f.write(f"file '{frag}'\n")

        carpeta_salida = f"{SMB_ROOT}/{expediente}/{id_sesion}"
        ensure_dir(carpeta_salida)
        salida = f"{carpeta_salida}/video2.webm"

        cmd = ffmpeg_concat_cmd(list_txt, salida)
        print("FFMPEG VIDEO2 CMD:", cmd)
        subprocess.run(cmd, shell=True, check=True, timeout=1800)

        if not os.path.exists(salida) or os.path.getsize(salida) < 1_000_000:
            raise Exception("video2.webm generado con tamaño insuficiente")

        registrar_archivo(id_sesion, "video2", normalizar_ruta(salida))
        finalizar_archivo(id_sesion, "video2", normalizar_ruta(salida))

        actualizar_job(job_id, estado="completado",
                       resultado=normalizar_ruta(salida))
        return True

    except Exception as e:
        print("ERROR unir_video2:", e)
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        return False

    finally:
        limpiar_temp(temp_dir)
