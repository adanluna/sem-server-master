import os
import shutil
import ffmpeg
from dotenv import load_dotenv
from celery import shared_task

# Cargar configuración desde .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
MIN_DISK_SPACE_GB = float(os.getenv("MIN_DISK_SPACE_GB", "5"))


def check_disk_space(path="/"):
    total, used, free = shutil.disk_usage(path)
    free_gb = free / (1024 ** 3)
    print(
        f"💾 Espacio libre en disco: {free_gb:.2f} GB (mínimo requerido: {MIN_DISK_SPACE_GB} GB)")
    return free_gb >= MIN_DISK_SPACE_GB


@shared_task(name="worker.unir_video.procesar_sesion_video")
def procesar_sesion_video(numero_expediente, id_sesion):
    """
    Une todos los videos en archivos_grabados y genera video_unido.webm
    en archivos/<numero_expediente>/<id_sesion>/videos, luego borra los fragmentos.
    """
    # Paths origen y destino
    origen_videos_path = f"/storage/archivos_grabados/{numero_expediente}/{id_sesion}/videos"
    destino_videos_path = f"/storage/archivos/{numero_expediente}/{id_sesion}/videos"

    # Asegurar carpeta destino
    os.makedirs(destino_videos_path, exist_ok=True)

    if not os.path.exists(origen_videos_path):
        raise Exception(f"⚠️ Carpeta no encontrada: {origen_videos_path}")

    if not check_disk_space("/"):
        raise Exception(
            "💥 No hay suficiente espacio en disco para procesar el video")

    # Buscar archivos de video
    video_files = sorted([
        os.path.join(origen_videos_path, f)
        for f in os.listdir(origen_videos_path)
        if f.lower().endswith((".mp4", ".mkv"))
    ])

    if not video_files:
        raise Exception(
            f"⚠️ No se encontraron archivos MP4 o MKV en: {origen_videos_path}")

    # Crear archivo de lista para ffmpeg
    list_file_path = os.path.join(origen_videos_path, "videos.txt")
    with open(list_file_path, "w") as f:
        for vf in video_files:
            f.write(f"file '{vf}'\n")

    output_path = os.path.join(destino_videos_path, "video_unido.webm")

    try:
        # ffmpeg concat
        ffmpeg.input(list_file_path, format='concat', safe=0).output(
            output_path, vcodec='libvpx', acodec='libvorbis', video_bitrate='1M'
        ).run(overwrite_output=True)

        if os.path.exists(output_path):
            print(f"✅ Video unido generado: {output_path}")

            # 🗑️ Borrar fragmentos originales
            for vf in video_files:
                os.remove(vf)
                print(f"🗑️ Fragmento eliminado: {vf}")

            # Borrar archivo lista
            os.remove(list_file_path)
            print(f"🗑️ Archivo de lista eliminado: {list_file_path}")

            return output_path
        else:
            raise Exception("⚠️ El archivo final no se generó correctamente.")

    except ffmpeg.Error as e:
        stderr_msg = e.stderr.decode() if e.stderr else str(e)
        raise Exception(f"💥 Error al unir video: {stderr_msg}")

    except Exception as e:
        raise Exception(f"💥 Error general: {e}")
