# ============================================================
#   SEMEFO — task.py (VERSIÓN PRO 2025)
#   Unión de fragmentos con detección de pausas, gaps y errores.
#   Genera video.webm / video2.webm en:
#       /mnt/wave/archivos_sistema_semefo/<expediente>/<id_sesion>/
# ============================================================

from .celery_app import celery_app
import subprocess
import os
import shutil
import json
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

SMB_ROOT = os.getenv("SMB_MOUNT", "/mnt/wave").rstrip("/")
TEMP_ROOT = "/tmp/semefo_temp"
FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", 4))
MODO_PRUEBA = os.getenv("MODO_PRUEBA_VIDEO", "0") == "1"

os.makedirs(TEMP_ROOT, exist_ok=True)


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
    if MODO_PRUEBA:
        return (
            f"ffmpeg -y -f concat -safe 0 -i \"{lista_txt}\" "
            f"-c:v libvpx-vp9 -b:v 1.5M -crf 35 -cpu-used 6 "
            f"-pix_fmt yuv420p -threads {FFMPEG_THREADS} \"{salida_webm}\""
        )
    else:
        return (
            f"ffmpeg -y -f concat -safe 0 -i \"{lista_txt}\" "
            f"-c:v libvpx-vp9 -b:v 3M -crf 28 -cpu-used 4 "
            f"-pix_fmt yuv420p -threads {FFMPEG_THREADS} \"{salida_webm}\""
        )


def construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion):
    """
    Filtra fragmentos por rango de sesión, detecta gaps y retorna lista ordenada.
    """
    seleccionados = []

    for frag in manifest["archivos"]:
        f_ini = datetime.fromisoformat(frag["inicio"])
        f_fin = datetime.fromisoformat(frag["fin"])

        # Condición de superposición de intervalos
        if f_fin >= inicio_sesion and f_ini <= fin_sesion:
            frag["_dt_ini"] = f_ini
            frag["_dt_fin"] = f_fin
            seleccionados.append(frag)

    if not seleccionados:
        raise Exception(
            "No se encontraron fragmentos compatibles con la sesión.")

    # Ordenar cronológicamente
    seleccionados.sort(key=lambda x: x["_dt_ini"])

    # ==========================
    #   DETECTAR GAPS y ERRORES
    # ==========================

    warnings = []
    for i in range(1, len(seleccionados)):
        prev = seleccionados[i - 1]
        curr = seleccionados[i]

        # Gap en segundos
        gap = (curr["_dt_ini"] - prev["_dt_fin"]).total_seconds()

        # Gap normal esperado: 0.0 - 0.2s (la cámara admite microsaltos)
        if gap > 0.5:
            warnings.append(
                f"GAP detectado de {gap:.2f}s entre {prev['archivo']} → {curr['archivo']}"
            )

        # Traslape inesperado
        if gap < -0.5:
            warnings.append(
                f"Traslape sospechoso de {-gap:.2f}s entre {prev['archivo']} y {curr['archivo']}"
            )

    if warnings:
        print("\n===== WARNINGS DE FRAGMENTOS =====")
        for w in warnings:
            print("[WARNING]", w)
        print("=================================\n")

    return seleccionados


# ============================================================
#   FUNCIÓN INTERNA PARA UNIR VIDEO 1 y 2
# ============================================================

def _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, tipo):
    temp_dir = os.path.join(TEMP_ROOT, f"{tipo}_{expediente}_{id_sesion}")
    limpiar_temp(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    job_id = None

    try:
        expediente = str(expediente)

        id_sesion = str(id_sesion)
        nombre_final = "video.webm" if tipo == "video" else "video2.webm"

        # Registrar job en API
        job_id = registrar_job(expediente, id_sesion, tipo, nombre_final)

        # Cargar manifest
        manifest = cargar_manifest(manifest_path)

        # Filtrar fragmentos
        frags = construir_lista_fragmentos(manifest, inicio_sesion, fin_sesion)

        # ============================
        #   COPIAR FRAGMENTOS
        # ============================

        lista_local = []

        for frag in frags:
            src = frag["ruta"]

            if not os.path.exists(src):
                raise Exception(f"Fragmento no existe en SMB: {src}")

            if os.path.getsize(src) < 50_000:
                raise Exception(f"Fragmento corrupto o incompleto: {src}")

            dst = os.path.join(temp_dir, os.path.basename(src))

            shutil.copy2(src, dst)
            lista_local.append(dst)

        # ============================
        #   CREAR list.txt
        # ============================

        list_txt = os.path.join(temp_dir, "list.txt")
        with open(list_txt, "w") as f:
            for p in lista_local:
                f.write(f"file '{p}'\n")

        # ============================
        #   EJECUTAR FFMPEG
        # ============================

        carpeta_salida = f"{SMB_ROOT}/archivos_sistema_semefo/{expediente}/{id_sesion}"
        ensure_dir(carpeta_salida)

        salida = f"{carpeta_salida}/{nombre_final}"

        cmd = ffmpeg_concat_cmd(list_txt, salida)
        print("\n========== FFMPEG CMD ==========")
        print(cmd)
        print("================================\n")

        subprocess.run(cmd, shell=True, check=True, timeout=3600)

        # Validación tamaño final
        if not os.path.exists(salida) or os.path.getsize(salida) < 1_000_000:
            raise Exception(
                f"{nombre_final} es demasiado pequeño. Error en conversión.")

        # Registrar archivo en API
        registrar_archivo(id_sesion, tipo, normalizar_ruta(salida))
        finalizar_archivo(id_sesion, tipo, normalizar_ruta(salida))

        actualizar_job(job_id, estado="completado",
                       resultado=normalizar_ruta(salida))
        return True

    except Exception as e:
        print(f"\n❌ ERROR unir_{tipo}: {e}\n")
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        return False

    finally:
        limpiar_temp(temp_dir)


# ============================================================
#   TAREAS CELERY PÚBLICAS
# ============================================================

@celery_app.task(name="worker.tasks.unir_video")
def unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video")


@celery_app.task(name="worker.tasks.unir_video2")
def unir_video2(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion):
    return _unir_video(expediente, id_sesion, manifest_path, inicio_sesion, fin_sesion, "video2")
