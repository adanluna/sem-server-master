
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
IS_DOCKER = os.getenv("IS_DOCKER", "0") == "1"
if IS_DOCKER:
    STORAGE_ROOT = "/storage"
else:
    STORAGE_ROOT = os.getenv(
        "STORAGE_ROOT", os.path.expanduser("~/semefo/storage"))


def normalizar_ruta_absoluta(ruta_completa):
    return ruta_completa.replace("\\", "/").replace(STORAGE_ROOT, "").lstrip(" /")


def send_to_whisper_queue(numero_expediente, id_sesion):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST))
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
    job_id = None
    try:
        numero_expediente = str(numero_expediente)
        id_sesion = str(id_sesion)
        base_path = f"{STORAGE_ROOT}/archivos_grabados/{numero_expediente}/{id_sesion}/audios"
        output_dir = f"{STORAGE_ROOT}/archivos/{numero_expediente}/{id_sesion}/audios"
        os.makedirs(output_dir, exist_ok=True)

        fragmentos = sorted(glob(os.path.join(base_path, "*.mp4")))
        if not fragmentos:
            print(f"⚠️ No hay fragmentos de audio para unir en {base_path}")
            job_id = registrar_job(
                numero_expediente, id_sesion, "audio", "audio.mp4")
            if job_id:
                actualizar_job(job_id, estado="error",
                               error="No hay fragmentos de audio")
            return

        for src_file in fragmentos:
            dst_file = os.path.join(output_dir, os.path.basename(src_file))
            if not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)

        fragmentos_convert = sorted(glob(os.path.join(output_dir, "*.mp4")))
        output_file = os.path.join(output_dir, "audio.mp4")
        fragmentos_convert = [
            f for f in fragmentos_convert if not f.endswith("audio.mp4")]

        lista_file = os.path.join(output_dir, "list_audio.txt")
        with open(lista_file, 'w') as f:
            for filepath in fragmentos_convert:
                f.write(f"file '{os.path.basename(filepath)}'\n")

        job_id = registrar_job(
            numero_expediente, id_sesion, "audio", "audio.mp4")
        cmd = f"cd {output_dir} && ffmpeg -y -f concat -safe 0 -i list_audio.txt -c copy audio.mp4"
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
                "Archivo de salida audio.mp4 no se generó correctamente")
    except Exception as e:
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        print(f"❌ Error al unir audio: {e}")


@celery_app.task(name="worker.tasks.unir_video")
def unir_video(numero_expediente, id_sesion):
    job_id = None
    try:
        numero_expediente = str(numero_expediente)
        id_sesion = str(id_sesion)
        base_path = f"{STORAGE_ROOT}/archivos_grabados/{numero_expediente}/{id_sesion}/videos"
        output_dir = f"{STORAGE_ROOT}/archivos/{numero_expediente}/{id_sesion}/videos"
        os.makedirs(output_dir, exist_ok=True)

        extensiones = ("*.avi", "*.mp4", "*.mkv", "*.mov", "*.webm")
        fragmentos = []
        for ext in extensiones:
            fragmentos.extend(glob(os.path.join(base_path, ext)))
        fragmentos = sorted(fragmentos)
        if not fragmentos:
            print(f"⚠️ No hay fragmentos de video para unir en {base_path}")
            job_id = registrar_job(
                numero_expediente, id_sesion, "video", "video.webm")
            if job_id:
                actualizar_job(job_id, estado="error",
                               error="No hay fragmentos de video")
            return

        for src_file in fragmentos:
            dst_file = os.path.join(output_dir, os.path.basename(src_file))
            if not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)

        fragmentos_convert = sorted(glob(os.path.join(output_dir, "*.mp4")))
        output_file = os.path.join(output_dir, "video.webm")
        fragmentos_convert = [
            f for f in fragmentos_convert if not f.endswith("video.webm")]

        lista_file = os.path.join(output_dir, "list_video.txt")
        with open(lista_file, 'w') as f:
            for filepath in fragmentos_convert:
                f.write(f"file '{os.path.basename(filepath)}'\n")

        job_id = registrar_job(
            numero_expediente, id_sesion, "video", "video.webm")

        cmd = generar_comando_video(output_dir, "list_video.txt", "video.webm")
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
                "Archivo de salida video.webm no se generó correctamente")
    except Exception as e:
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        print(f"❌ Error al unir video: {e}")


@celery_app.task(name="worker.tasks.unir_video2", queue="videos2")
def unir_video2(numero_expediente, id_sesion):
    job_id_video = None
    job_id_audio = None
    try:
        numero_expediente = str(numero_expediente)
        id_sesion = str(id_sesion)

        carpeta_sesion = os.path.join(
            STORAGE_ROOT, "archivos_grabados", numero_expediente, id_sesion, "videos2")
        carpeta_destino_video = os.path.join(
            STORAGE_ROOT, "archivos", numero_expediente, id_sesion, "videos")
        carpeta_destino_audio = os.path.join(
            STORAGE_ROOT, "archivos", numero_expediente, id_sesion, "audios")
        carpeta_fragmentos_video2 = os.path.join(
            carpeta_destino_video, "video2_fragments")

        os.makedirs(carpeta_destino_video, exist_ok=True)
        os.makedirs(carpeta_destino_audio, exist_ok=True)
        os.makedirs(carpeta_fragmentos_video2, exist_ok=True)

        ruta_video = os.path.join(carpeta_destino_video, "video2.webm")
        ruta_audio = os.path.join(carpeta_destino_audio, "audio2.mp4")

        # Buscar fragmentos
        extensiones = ("*.avi", "*.mp4", "*.mkv", "*.mov", "*.webm")
        archivos_videos = []
        for ext in extensiones:
            archivos_videos.extend(glob(os.path.join(carpeta_sesion, ext)))
        archivos_videos = sorted(archivos_videos)

        if not archivos_videos:
            print(
                f"⚠️ No se encontraron fragmentos de video2 en {carpeta_sesion}")
            job_id = registrar_job(
                numero_expediente, id_sesion, "video2", "video2.webm")
            if job_id:
                actualizar_job(job_id, estado="error",
                               error="No se encontraron archivos de video2")
            return False

        # Copiar fragmentos a carpeta temporal
        for archivo in archivos_videos:
            dst = os.path.join(carpeta_fragmentos_video2,
                               os.path.basename(archivo))
            if not os.path.exists(dst):
                shutil.copy2(archivo, dst)

        fragmentos_convert = sorted(
            glob(os.path.join(carpeta_fragmentos_video2, "*.mp4")))
        lista_inputs = os.path.join(
            carpeta_fragmentos_video2, "list_video2.txt")
        with open(lista_inputs, "w", encoding="utf-8") as f:
            for archivo in fragmentos_convert:
                f.write(f"file '{os.path.basename(archivo)}'\n")

        ruta_rel_video = os.path.relpath(
            ruta_video, STORAGE_ROOT).replace("\\", "/")
        ruta_rel_audio = os.path.relpath(
            ruta_audio, STORAGE_ROOT).replace("\\", "/")

        # Registrar ambos jobs al inicio
        job_id_video = registrar_job(
            numero_expediente, id_sesion, "video2", "video2.webm")
        if not job_id_video:
            raise Exception("❌ No se pudo registrar job de video2")

        job_id_audio = registrar_job(
            numero_expediente, id_sesion, "audio2", "audio2.mp4")
        if not job_id_audio:
            raise Exception("❌ No se pudo registrar job de audio2")

        # Ejecutar ffmpeg para unir video
        print(f"🎬 Uniendo fragmentos de video2 en {ruta_video}")
        cmd = generar_comando_video(
            carpeta_fragmentos_video2, "list_video2.txt", ruta_video)
        subprocess.run(cmd, shell=True, check=True)
        os.remove(lista_inputs)

        if not os.path.exists(ruta_video):
            raise Exception("❌ No se generó archivo video2.webm")

        print(f"🔊 Extrayendo audio de video2 a {ruta_audio}")
        subprocess.run(["ffmpeg", "-i", ruta_video, "-vn",
                       "-acodec", "aac", ruta_audio], check=True)

        if not os.path.exists(ruta_audio):
            raise Exception("❌ No se generó archivo audio2.mp4")

        # Finalizar video2
        registrar_archivo(id_sesion, "video2", ruta_rel_video, ruta_rel_video)
        finalizar_archivo(id_sesion, "video2", ruta_rel_video)
        actualizar_job(job_id_video, estado="completado",
                       resultado=ruta_rel_video)

        # Finalizar audio2
        registrar_archivo(id_sesion, "audio2", ruta_rel_audio, ruta_rel_audio)
        finalizar_archivo(id_sesion, "audio2", ruta_rel_audio)
        actualizar_job(job_id_audio, estado="completado",
                       resultado=ruta_rel_audio)

        # Eliminar carpeta temporal de fragmentos
        if os.path.exists(carpeta_fragmentos_video2):
            shutil.rmtree(carpeta_fragmentos_video2)

        print(
            f"✅ Video2 y audio2 procesados correctamente para sesión {id_sesion}")
        return True

    except Exception as e:
        print(f"❌ Error procesando video2/audio2 para sesión {id_sesion}: {e}")
        try:
            if 'job_id_video' in locals() and job_id_video:
                actualizar_job(job_id_video, estado="error", error=str(e))
        except Exception as ex:
            print(f"⚠️ Error al registrar o actualizar job de video2: {ex}")
        return False


def generar_comando_video(output_dir: str, lista_input: str, nombre_salida: str = "video.webm") -> str:
    """
    Genera el comando ffmpeg para unir video en función del modo prueba.
    """
    if MODO_PRUEBA_VIDEO:
        return (
            f"cd {output_dir} && "
            f"ffmpeg -y -f concat -safe 0 -i {lista_input} "
            f"-f lavfi -i anullsrc=r=44100:cl=mono "
            f"-shortest -c:v libvpx -pix_fmt yuv420p -b:v 200k -cpu-used 8 -deadline realtime "
            f"-c:a libvorbis -b:a 64k {nombre_salida}"
        )
    else:
        return (
            f"cd {output_dir} && "
            f"ffmpeg -y -f concat -safe 0 -i {lista_input} "
            f"-c:v libvpx -pix_fmt yuv420p -b:v 4M -vf scale=1920:1080 "
            f"-cpu-used 4 -deadline good -c:a libvorbis -b:a 128k {nombre_salida}"
        )
