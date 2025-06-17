from .celery_app import celery_app


@celery_app.task
def transcribir_audio(path):
    # Simulación
    return f"Transcripción simulada para: {path}"
