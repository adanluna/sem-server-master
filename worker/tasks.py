from .celery_app import celery_app
import subprocess
import os
import shutil
from glob import glob
from dotenv import load_dotenv
import pika
import json

from worker.job_api_client import registrar_job, actualizar_job, finalizar_archivo, registrar_archivo

load_dotenv()

MODO_PRUEBA_VIDEO = os.getenv("MODO_PRUEBA_VIDEO", "0") == "1"
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "192.168.1.220")
QUEUE_NAME = os.getenv("QUEUE_NAME", "transcripciones")
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/storage")


def normalizar_ruta_absoluta(ruta_completa):
    return ruta_completa.replace("\\", "/").replace(STORAGE_ROOT, "").lstrip("/")


def send_to_whisper_queue(numero_expediente, id_sesion):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        message = json.dumps({
            "numero_expediente": numero_expediente,
            "id_sesion": id_sesion,
            "filename": "audio.mp4"
        })
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(
            f"🚀 Enviado a cola {QUEUE_NAME} -> {numero_expediente}/{id_sesion}")
        connection.close()
    except Exception as e:
        print(f"💥 Error enviando a Whisper: {e}")


@celery_app.task(name="worker.tasks.unir_audio")
def unir_audio(numero_expediente, id_sesion):
    base_path = f"{STORAGE_ROOT}/archivos_grabados/{numero_expediente}/{id_sesion}/audios"
    output_dir = f"{STORAGE_ROOT}/archivos/{numero_expediente}/{id_sesion}/audios"
    os.makedirs(output_dir, exist_ok=True)

    fragmentos = sorted(glob(os.path.join(base_path, "*.mp4")))
    if not fragmentos:
        print(f"⚠️ No hay fragmentos de audio para unir en {base_path}")
        return

    for src_file in fragmentos:
        dst_file = os.path.join(output_dir, os.path.basename(src_file))
        if not os.path.exists(dst_file):
            shutil.copy2(src_file, dst_file)

    fragmentos_convert = sorted(glob(os.path.join(output_dir, "*.mp4")))
    output_file = os.path.join(output_dir, "audio.mp4")
    fragmentos_convert = [
        f for f in fragmentos_convert if not f.endswith("audio.mp4")]

    lista_file = os.path.join(output_dir, "input_list.txt")
    with open(lista_file, 'w') as f:
        for filepath in fragmentos_convert:
            f.write(f"file '{os.path.basename(filepath)}'\n")

    job_id = registrar_job(numero_expediente, id_sesion, "audio", "audio.mp4")
    try:
        cmd = f"cd {output_dir} && ffmpeg -y -f concat -safe 0 -i input_list.txt -c copy audio.mp4"
        subprocess.run(cmd, shell=True, check=True)

        if os.path.exists(lista_file):
            os.remove(lista_file)

        if os.path.exists(output_file) and os.path.getsize(output_file) > 1 * 1024 * 1024:
            for f in fragmentos_convert:
                os.remove(f)

            ruta_relativa = normalizar_ruta_absoluta(output_file)
            registrar_archivo(id_sesion, "audio", ruta_relativa)
            finalizar_archivo(id_sesion, "audio", ruta_relativa)
            if job_id:
                actualizar_job(job_id, estado="completado",
                               resultado=ruta_relativa)
            send_to_whisper_queue(numero_expediente, id_sesion)
        else:
            raise Exception(
                "⚠️ El archivo de salida audio.mp4 no se generó correctamente")
    except Exception as e:
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        print(f"❌ Error al unir audio: {e}")


@celery_app.task(name="worker.tasks.unir_video")
def unir_video(numero_expediente, id_sesion):
    base_path = f"{STORAGE_ROOT}/archivos_grabados/{numero_expediente}/{id_sesion}/videos"
    output_dir = f"{STORAGE_ROOT}/archivos/{numero_expediente}/{id_sesion}/videos"
    os.makedirs(output_dir, exist_ok=True)

    fragmentos = sorted(glob(os.path.join(base_path, "*.mp4")))
    if not fragmentos:
        print(f"⚠️ No hay fragmentos de video para unir en {base_path}")
        return

    for src_file in fragmentos:
        dst_file = os.path.join(output_dir, os.path.basename(src_file))
        if not os.path.exists(dst_file):
            shutil.copy2(src_file, dst_file)

    fragmentos_convert = sorted(glob(os.path.join(output_dir, "*.mp4")))
    output_file = os.path.join(output_dir, "video.webm")
    fragmentos_convert = [
        f for f in fragmentos_convert if not f.endswith("video.webm")]

    lista_file = os.path.join(output_dir, "input_list.txt")
    with open(lista_file, 'w') as f:
        for filepath in fragmentos_convert:
            f.write(f"file '{os.path.basename(filepath)}'\n")

    job_id = registrar_job(numero_expediente, id_sesion, "video", "video.webm")
    try:
        if MODO_PRUEBA_VIDEO:
            cmd = f"cd {output_dir} && ffmpeg -y -f concat -safe 0 -i input_list.txt -c:v libvpx -pix_fmt yuv420p -b:v 200k -cpu-used 8 -deadline realtime -an video.webm"
        else:
            cmd = f"cd {output_dir} && ffmpeg -y -f concat -safe 0 -i input_list.txt -c:v libvpx -pix_fmt yuv420p -b:v 4M -vf scale=1920:1080 -cpu-used 4 -deadline good -c:a libvorbis -b:a 128k video.webm"

        subprocess.run(cmd, shell=True, check=True)

        if os.path.exists(lista_file):
            os.remove(lista_file)

        if os.path.exists(output_file) and os.path.getsize(output_file) > 1 * 1024 * 1024:
            for f in fragmentos_convert:
                os.remove(f)

            ruta_relativa = normalizar_ruta_absoluta(output_file)
            registrar_archivo(id_sesion, "video", ruta_relativa)
            finalizar_archivo(id_sesion, "video", ruta_relativa)
            if job_id:
                actualizar_job(job_id, estado="completado",
                               resultado=ruta_relativa)
        else:
            raise Exception(
                "⚠️ El archivo de salida video.webm no se generó correctamente")
    except Exception as e:
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        print(f"❌ Error al unir video: {e}")
