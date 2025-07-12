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


@shared_task(name="worker.unir_audio.procesar_sesion_audio")
def procesar_sesion_audio(numero_expediente, id_sesion):
    """
    Une todos los audios de archivos_grabados y genera un audio_unido.mp4
    en archivos/<numero_expediente>/<id_sesion>/audios/, luego borra los fragmentos.
    """
    # Paths origen y destino
    origen_audios_path = f"/storage/archivos_grabados/{numero_expediente}/{id_sesion}/audios"
    destino_audios_path = f"/storage/archivos/{numero_expediente}/{id_sesion}/audios"

    # Asegurar carpetas destino
    os.makedirs(destino_audios_path, exist_ok=True)

    if not os.path.exists(origen_audios_path):
        raise Exception(f"⚠️ Carpeta no encontrada: {origen_audios_path}")

    if not check_disk_space("/"):
        raise Exception(
            "💥 No hay suficiente espacio en disco para procesar el audio")

    # Buscar archivos de audio
    audio_files = sorted([
        os.path.join(origen_audios_path, f)
        for f in os.listdir(origen_audios_path)
        if f.lower().endswith((".wav", ".mp3"))
    ])

    if not audio_files:
        raise Exception(
            f"⚠️ No se encontraron archivos WAV o MP3 en: {origen_audios_path}")

    # Crear archivo lista para ffmpeg
    list_file_path = os.path.join(origen_audios_path, "audios.txt")
    with open(list_file_path, "w") as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")

    output_path = os.path.join(destino_audios_path, "audio_unido.mp4")

    try:
        # ffmpeg concat
        ffmpeg.input(list_file_path, format='concat', safe=0).output(
            output_path, acodec='aac', audio_bitrate='192k'
        ).run(overwrite_output=True)

        if os.path.exists(output_path):
            print(f"✅ Audio unido generado: {output_path}")

            # 🗑️ Borrar fragmentos originales
            for af in audio_files:
                os.remove(af)
                print(f"🗑️ Fragmento eliminado: {af}")

            # Borrar archivo lista
            os.remove(list_file_path)
            print(f"🗑️ Archivo de lista eliminado: {list_file_path}")

            return output_path
        else:
            raise Exception("⚠️ El archivo final no se generó correctamente.")

    except ffmpeg.Error as e:
        stderr_msg = e.stderr.decode() if e.stderr else str(e)
        raise Exception(f"💥 Error al unir audio: {stderr_msg}")

    except Exception as e:
        raise Exception(f"💥 Error general: {e}")
