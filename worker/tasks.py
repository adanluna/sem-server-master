from .celery_app import celery_app
import os
import subprocess


@celery_app.task
def unir_audio(numero_expediente, id_sesion):
    base_path = f"/storage/archivos/{numero_expediente}/{id_sesion}/audios"
    output_file = os.path.join(base_path, "audio.mp4")
    input_pattern = f"/storage/archivos_grabados/{numero_expediente}/{id_sesion}/audios/*.wav"

    # Ejemplo de unir con ffmpeg (ajústalo según tus fragmentos reales)
    cmd = f"ffmpeg -y -i 'concat:{input_pattern}' -c copy {output_file}"
    subprocess.run(cmd, shell=True, check=True)
    return f"✅ Audio unido en: {output_file}"


@celery_app.task
def unir_video(numero_expediente, id_sesion):
    base_path = f"/storage/archivos/{numero_expediente}/{id_sesion}/videos"
    output_file = os.path.join(base_path, "video.webm")
    input_pattern = f"/storage/archivos_grabados/{numero_expediente}/{id_sesion}/videos/*.mp4"

    cmd = f"ffmpeg -y -i 'concat:{input_pattern}' -c copy {output_file}"
    subprocess.run(cmd, shell=True, check=True)
    return f"✅ Video unido en: {output_file}"


@celery_app.task
def transcribir_audio(numero_expediente, id_sesion):
    audio_file = f"/storage/archivos/{numero_expediente}/{id_sesion}/audios/audio.mp4"
    output_dir = f"/storage/archivos/{numero_expediente}/{id_sesion}/transcripcion"

    os.makedirs(output_dir, exist_ok=True)
    cmd = f"whisper {audio_file} --language Spanish --output_format txt --output_dir {output_dir}"
    subprocess.run(cmd, shell=True, check=True)
    return f"✅ Transcripción generada en: {output_dir}"
