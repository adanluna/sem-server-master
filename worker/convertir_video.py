import os
import ffmpeg
from dotenv import load_dotenv
from celery import shared_task

# Cargar .env desde la raíz del proyecto
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

VIDEOS_DIR = os.getenv("VIDEOS_DIR", "storage/videos")
VIDEOS_WEBM_DIR = os.getenv("VIDEOS_WEBM_DIR", "storage/videos_webm")
# os.makedirs(VIDEOS_WEBM_DIR, exist_ok=True)


@shared_task(name="worker.convertir_video.convertir_video")
def convertir_video(nombre_archivo):
    input_path = os.path.join(VIDEOS_DIR, nombre_archivo)
    output_name = os.path.splitext(nombre_archivo)[0] + ".webm"
    output_path = os.path.join(VIDEOS_WEBM_DIR, output_name)

    if not os.path.exists(input_path):
        print(f"⚠️ Archivo no encontrado: {input_path}")
        return None

    try:
        ffmpeg.input(input_path).output(
            output_path, vcodec='libvpx', acodec='libvorbis', video_bitrate='1M'
        ).run(overwrite_output=True)

        if os.path.exists(output_path):
            return f"✅ Conversión completada: {output_path}"
        else:
            return f"⚠️ Error: El archivo convertido no se generó correctamente."
    except ffmpeg.Error as e:
        return f"💥 Error al convertir {nombre_archivo}: {e.stderr.decode()}"
