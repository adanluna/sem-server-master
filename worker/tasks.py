from .celery_app import celery_app
import subprocess
import os
import shutil
from glob import glob
from dotenv import load_dotenv
import pika
import json
import time

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
            f"\U0001f680 Enviado a cola {QUEUE_NAME} -> {numero_expediente}/{id_sesion}")
        connection.close()
    except Exception as e:
        print(f"\U0001f4a5 Error enviando a Whisper: {e}")


@celery_app.task(name="worker.tasks.unir_audio")
def unir_audio(numero_expediente, id_sesion):
    job_id = None
    try:
        numero_expediente = str(numero_expediente)
        id_sesion = str(id_sesion)
        base_path = f"{STORAGE_ROOT}/archivos_grabados/{numero_expediente}/{id_sesion}/audios"
        output_dir = f"{STORAGE_ROOT}/archivos/{numero_expediente}/{id_sesion}/audios"
        os.makedirs(output_dir, exist_ok=True)

        fragmentos = sorted(esperar_archivos_completos(base_path))
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
        subprocess.run(cmd, shell=True, check=True, timeout=600)

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
    finally:
        try:
            if os.path.exists(lista_file):
                os.remove(lista_file)
        except:
            pass


@celery_app.task(name="worker.tasks.unir_video")
def unir_video(numero_expediente, id_sesion):
    job_id = None
    lista_file = None
    try:
        numero_expediente = str(numero_expediente)
        id_sesion = str(id_sesion)

        base_path = os.path.join(
            STORAGE_ROOT, "archivos_grabados", numero_expediente, id_sesion, "videos")
        output_dir = os.path.join(
            STORAGE_ROOT, "archivos", numero_expediente, id_sesion, "videos")
        os.makedirs(output_dir, exist_ok=True)

        extensiones = ("*.avi", "*.mp4", "*.mkv", "*.mov", "*.webm")
        fragmentos = []
        for ext in extensiones:
            fragmentos.extend(esperar_archivos_completos(
                base_path, extension=ext))
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

        fragmentos_convert = []
        for ext in extensiones:
            fragmentos_convert.extend(
                sorted(glob(os.path.join(output_dir, ext))))
        fragmentos_convert = [
            f for f in fragmentos_convert if not f.endswith("video.webm")]

        if not fragmentos_convert:
            raise Exception("❌ No hay fragmentos convertidos para unir")

        lista_file = os.path.join(output_dir, "list_video.txt")
        with open(lista_file, 'w') as f:
            for filepath in fragmentos_convert:
                f.write(f"file '{os.path.basename(filepath)}'\n")

        output_file = os.path.join(output_dir, "video.webm")
        ruta_relativa = normalizar_ruta_absoluta(output_file)

        job_id = registrar_job(
            numero_expediente, id_sesion, "video", "video.webm")

        cmd = generar_comando_video(output_dir, "list_video.txt", "video.webm")
        print(f"🎬 Ejecutando comando ffmpeg para video:\n{cmd}")
        subprocess.run(cmd, shell=True, check=True, timeout=300)

        if not os.path.exists(output_file) or os.path.getsize(output_file) < 500_000:
            raise Exception(
                "❌ No se generó archivo video.webm o su tamaño es insuficiente")

        # ✅ CAMBIO: Solo borrar archivos que están en list_video.txt
        print("🗑️ Borrando fragmentos de video listados en list_video.txt...")
        try:
            with open(lista_file, "r") as f:
                archivos_borrados = 0
                for line in f:
                    # Extraer nombre del archivo de la línea "file 'nombre.mp4'"
                    if line.strip().startswith("file '") and line.strip().endswith("'"):
                        # Quitar "file '" y "'"
                        nombre_archivo = line.strip()[6:-1]
                        ruta_completa = os.path.join(
                            output_dir, nombre_archivo)

                        if os.path.exists(ruta_completa):
                            print(f"   🗑️ Borrando: {nombre_archivo}")
                            os.remove(ruta_completa)
                            archivos_borrados += 1
                        else:
                            print(f"   ⚠️ No se encontró: {nombre_archivo}")

                print(f"✅ Se borraron {archivos_borrados} fragmentos de video")

        except Exception as e:
            print(f"⚠️ Error al borrar fragmentos: {e}")

        registrar_archivo(id_sesion, "video", ruta_relativa)
        finalizar_archivo(id_sesion, "video", ruta_relativa)
        if job_id:
            actualizar_job(job_id, estado="completado",
                           resultado=ruta_relativa)

        print(f"✅ Video procesado correctamente para sesión {id_sesion}")

    except subprocess.TimeoutExpired:
        if job_id:
            actualizar_job(job_id, estado="error",
                           error="Tiempo excedido en ffmpeg")
        print("❌ Error: ffmpeg excedió el tiempo límite (timeout)")

    except Exception as e:
        if job_id:
            actualizar_job(job_id, estado="error", error=str(e))
        print(f"❌ Error al unir video: {e}")

    finally:
        # ✅ CAMBIO: Borrar list_video.txt al final
        try:
            if lista_file and os.path.exists(lista_file):
                print("🗑️ Borrando archivo de lista: list_video.txt")
                os.remove(lista_file)
                print("✅ Archivo list_video.txt borrado")
        except Exception as e:
            print(f"⚠️ Error al borrar list_video.txt: {e}")


@celery_app.task(name="worker.tasks.unir_video2", queue="videos2")
def unir_video2(numero_expediente, id_sesion):
    job_id_video = None
    job_id_audio = None
    lista_inputs = None
    carpeta_fragmentos_video2 = None

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

        # ✅ CAMBIO: Archivo final en la carpeta correcta
        ruta_video = os.path.join(carpeta_destino_video, "video2.webm")
        ruta_audio = os.path.join(carpeta_destino_audio, "audio2.mp4")

        extensiones = ("*.avi", "*.mp4", "*.mkv", "*.mov", "*.webm")
        archivos_videos = []
        for ext in extensiones:
            archivos_videos.extend(esperar_archivos_completos(
                carpeta_sesion, extension=ext))
        archivos_videos = sorted(archivos_videos)

        if not archivos_videos:
            print(
                f"⚠️ No se encontraron fragmentos de video2 en {carpeta_sesion}")
            job_id_video = registrar_job(
                numero_expediente, id_sesion, "video2", "video2.webm")
            if job_id_video:
                actualizar_job(job_id_video, estado="error",
                               error="No se encontraron archivos de video2")
            return False

        for archivo in archivos_videos:
            dst = os.path.join(carpeta_fragmentos_video2,
                               os.path.basename(archivo))
            if not os.path.exists(dst):
                shutil.copy2(archivo, dst)

        fragmentos_convert = sorted(
            glob(os.path.join(carpeta_fragmentos_video2, "*.mp4")))
        if not fragmentos_convert:
            raise Exception(
                "❌ No hay archivos .mp4 en carpeta de fragmentos para unir")

        lista_inputs = os.path.join(
            carpeta_fragmentos_video2, "list_video2.txt")
        with open(lista_inputs, "w", encoding="utf-8") as f:
            for archivo in fragmentos_convert:
                f.write(f"file '{os.path.basename(archivo)}'\n")

        ruta_rel_video = os.path.relpath(
            ruta_video, STORAGE_ROOT).replace("\\", "/")
        ruta_rel_audio = os.path.relpath(
            ruta_audio, STORAGE_ROOT).replace("\\", "/")

        job_id_video = registrar_job(
            numero_expediente, id_sesion, "video2", "video2.webm")
        job_id_audio = registrar_job(
            numero_expediente, id_sesion, "audio2", "audio2.mp4")

        # ✅ CAMBIO: Generar comando que guarde en la ruta final correcta
        cmd = generar_comando_video(
            carpeta_fragmentos_video2, "list_video2.txt", ruta_video)
        print(f"🎬 Ejecutando comando ffmpeg para video2:\n{cmd}")
        subprocess.run(cmd, shell=True, check=True, timeout=600)

        # ✅ CAMBIO: Verificar que el archivo esté en la ubicación correcta
        if not os.path.exists(ruta_video):
            raise Exception(f"❌ No se encontró video2.webm en {ruta_video}")

        file_size = os.path.getsize(ruta_video)
        if file_size < 1 * 1024 * 1024:  # 1MB mínimo
            raise Exception(
                f"❌ Archivo video2.webm muy pequeño: {file_size} bytes")

        print(
            f"✅ Video2.webm creado exitosamente: {file_size / (1024*1024):.2f} MB")

        # Extraer audio del video final
        print("🎵 Extrayendo audio de video2.webm...")
        cmd_audio = f"ffmpeg -y -i \"{ruta_video}\" -vn -acodec aac \"{ruta_audio}\""
        subprocess.run(cmd_audio, shell=True, check=True, timeout=600)

        if not os.path.exists(ruta_audio) or os.path.getsize(ruta_audio) < 100 * 1024:
            raise Exception("❌ No se generó archivo audio2.mp4 o está vacío")

        print(
            f"✅ Audio2.mp4 extraído: {os.path.getsize(ruta_audio) / (1024*1024):.2f} MB")

        # ✅ CAMBIO: Solo borrar fragmentos que están en list_video2.txt
        print("🗑️ Borrando fragmentos de video2 listados en list_video2.txt...")
        try:
            with open(lista_inputs, "r") as f:
                archivos_borrados = 0
                for line in f:
                    if line.strip().startswith("file '") and line.strip().endswith("'"):
                        # Quitar "file '" y "'"
                        nombre_archivo = line.strip()[6:-1]
                        ruta_completa = os.path.join(
                            carpeta_fragmentos_video2, nombre_archivo)

                        if os.path.exists(ruta_completa):
                            print(f"   🗑️ Borrando: {nombre_archivo}")
                            os.remove(ruta_completa)
                            archivos_borrados += 1
                        else:
                            print(f"   ⚠️ No se encontró: {nombre_archivo}")

                print(
                    f"✅ Se borraron {archivos_borrados} fragmentos de video2")

        except Exception as e:
            print(f"⚠️ Error al borrar fragmentos: {e}")

        registrar_archivo(id_sesion, "video2", ruta_rel_video)
        finalizar_archivo(id_sesion, "video2", ruta_rel_video)
        actualizar_job(job_id_video, estado="completado",
                       resultado=ruta_rel_video)

        registrar_archivo(id_sesion, "audio2", ruta_rel_audio)
        finalizar_archivo(id_sesion, "audio2", ruta_rel_audio)
        actualizar_job(job_id_audio, estado="completado",
                       resultado=ruta_rel_audio)

        print(
            f"✅ Video2 y audio2 procesados correctamente para sesión {id_sesion}")
        return True

    except Exception as e:
        print(f"❌ Error procesando video2/audio2 para sesión {id_sesion}: {e}")
        if job_id_video:
            actualizar_job(job_id_video, estado="error", error=str(e))
        if job_id_audio:
            actualizar_job(job_id_audio, estado="error", error=str(e))
        return False

    finally:
        # ✅ CAMBIO: Limpiar archivos de lista y carpeta temporal
        try:
            if lista_inputs and os.path.exists(lista_inputs):
                print("🗑️ Borrando archivo de lista: list_video2.txt")
                os.remove(lista_inputs)
                print("✅ Archivo list_video2.txt borrado")
        except Exception as e:
            print(f"⚠️ Error al borrar list_video2.txt: {e}")

        try:
            if carpeta_fragmentos_video2 and os.path.exists(carpeta_fragmentos_video2):
                print("🗑️ Borrando carpeta temporal de fragmentos...")
                shutil.rmtree(carpeta_fragmentos_video2, ignore_errors=True)
                print("✅ Carpeta temporal borrada")
        except Exception as e:
            print(f"⚠️ Error al borrar carpeta temporal: {e}")


def generar_comando_video(output_dir: str, lista_input: str, nombre_salida: str = "video.webm") -> str:
    """
    Generar comando ffmpeg para unir videos
    - Si nombre_salida contiene '/', se trata como ruta completa
    - Si no, se trata como nombre relativo al output_dir
    """
    # Leer configuración del .env
    ffmpeg_threads = int(os.getenv('FFMPEG_THREADS', 4))

    # Determinar si es ruta completa o relativa
    if '/' in nombre_salida or '\\' in nombre_salida:
        # Ruta completa especificada
        salida_final = f"\"{nombre_salida}\""
    else:
        # Nombre relativo
        salida_final = nombre_salida

    if MODO_PRUEBA_VIDEO:
        # 🚀 Modo PRUEBA: Rápido, optimizado para Mac M1, formato WebM
        return (
            f"cd {output_dir} && "
            f"ffmpeg -y -f concat -safe 0 -i {lista_input} "
            f"-c:v libvpx-vp9 -b:v 1.5M -crf 35 "
            f"-cpu-used 6 -deadline realtime "
            f"-row-mt 1 -tile-columns 2 -tile-rows 1 "
            f"-vf scale=1280:720 -pix_fmt yuv420p "
            f"-c:a libopus -b:a 96k -ac 2 "
            f"-threads {ffmpeg_threads} "
            f"{salida_final}"
        )
    else:
        # 🎯 Modo PRODUCCIÓN: Calidad alta, formato WebM optimizado
        return (
            f"cd {output_dir} && "
            f"ffmpeg -y -f concat -safe 0 -i {lista_input} "
            f"-c:v libvpx-vp9 -b:v 3M -crf 28 "
            f"-cpu-used 4 -deadline good "
            f"-row-mt 1 -tile-columns 3 -tile-rows 2 "
            f"-vf scale=1920:1080 -pix_fmt yuv420p "
            f"-c:a libopus -b:a 128k -ac 2 "
            f"-threads {ffmpeg_threads} "
            f"{salida_final}"
        )


def esperar_archivos_completos(ruta, extension="*.mp4", intentos=10, delay=0.5, minimo_tamano_bytes=1024 * 100):
    for intento in range(intentos):
        archivos = glob(os.path.join(ruta, extension))
        if archivos and all(os.path.getsize(f) >= minimo_tamano_bytes for f in archivos):
            return archivos
        time.sleep(delay)
    return []
