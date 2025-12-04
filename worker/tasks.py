# ============================================================
#   SEMEFO — task.py (FINAL CORREGIDO)
#   Server Master
#   Une fragmentos MKV según MANIFEST y genera video.webm/video2.webm
#   Guardando SIEMPRE en:
#       /mnt/wave/archivos_sistema_semefo/<expediente>/<id_sesion>/
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

# Nueva ruta real del SMB
SMB_ROOT = os.getenv("SMB_MOUNT", "/mnt/wave").rstrip("/")

FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", 4))
MODO_PRUEBA = os.getenv("MODO_PRUEBA_VIDEO", "0") == "1"

TEMP_ROOT = "/tmp/semefo_temp"
os.makedirs(TEMP_ROOT, exist_ok=True)

GRABADOR_UUID = os.getenv("GRABADOR_UUID", "").strip()


# ============================================================
#   UTILIDADES
# ============================================================

def cargar_manifest(manifest_path):
    """Carga manifest.json desde el SMB."""
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"No existe manifest: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ffmpeg_concat_cmd(lista_txt, salida_webm):
    """Comando final FFMPEG."""
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
    """Devuelve fragmentos cuyo tiempo intersecta la sesión."""
    seleccionados = []

    for frag in manifest["archivos"]:
        f_ini = frag["inicio"]
        f_fin = frag["fin"]

        if f_fin >= inicio_sesion and f_ini <= fin_sesion:
            seleccionados.append(frag)

    if not seleccionados:
        raise Exception(
            "No se encontraron fragmentos para el rango solicitado")

    seleccionados.sort(key=lambda x: x["inicio"])
    return seleccionados


# ============================================================
#   FUNCIÓN PRINCIPAL DE UNIÓN DE VIDEO
# ============================================================

def _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, tipo):
    """
    tipo = "video"  → video.webm
    tipo = "video2" → video2.webm
    """

    temp_dir = os.path.join(TEMP_ROOT, f"{tipo}_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    job_id = None

    try:
        expediente = str(expediente)
        id_sesion = str(id_sesion)

        # Registrar job en API
        nombre_final = "video.webm" if tipo == "video" else "video2.webm"
        job_id = registrar_job(expediente, id_sesion, tipo, nombre_final)

        # Cargar manifest
        manifest = cargar_manifest(manifest_path)

        # Seleccionar fragmentos
        frags = construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion)

        # Copiar fragmentos al TEMP
        lista_local = []
        for frag in frags:
            ruta_rel = frag["ruta_relativa"]
            src = os.path.join(SMB_ROOT, ruta_rel)

            if not os.path.exists(src):
                raise Exception(f"Fragmento no encontrado en SMB: {src}")

            dst = os.path.join(temp_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            lista_local.append(dst)

        # Crear list.txt
        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for frag in lista_local:
                f.write(f"file '{frag}'\n")

        # Carpeta destino REAL en SMB
        carpeta_salida = f"{SMB_ROOT}/archivos_sistema_semefo/{expediente}/{id_sesion}"
        ensure_dir(carpeta_salida)

        salida = f"{carpeta_salida}/{nombre_final}"

        # FFMPEG
        cmd = ffmpeg_concat_cmd(list_txt, salida)
        print("FFMPEG CMD:", cmd)
        subprocess.run(cmd, shell=True, check=True, timeout=1800)

        # Validar tamaño
        if not os.path.exists(salida) or os.path.getsize(salida) < 1_000_000:
            raise Exception(f"{nombre_final} generado con tamaño insuficiente")

        registrar_archivo(id_sesion, tipo, normalizar_ruta(salida))
        finalizar_archivo(id_sesion, tipo, normalizar_ruta(salida))

        actualizar_job(job_id, estado="completado",
                       resultado=normalizar_ruta(salida))
        return True

    except Exception as e:
        print(f"ERROR unir_{tipo}:", e)
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        return False

    finally:
        limpiar_temp(temp_dir)


# ============================================================
#   TAREAS CELERY
# ============================================================

@celery_app.task(name="worker.tasks.unir_video")
def unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video")


@celery_app.task(name="worker.tasks.unir_video2")
def unir_video2(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video2")
