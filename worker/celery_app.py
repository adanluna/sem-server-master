from celery import Celery
import os

# El broker debe venir SIEMPRE desde RABBITMQ_URL (variable unificada)
BROKER_URL = os.getenv("RABBITMQ_URL")

# Backend en postgres (igual para workers Docker y Mac)
RESULT_BACKEND = (
    f"db+postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

celery_app = Celery(
    "worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "worker.tasks",
        "worker.manifest_builder"
    ]
)

# ⭐ Rutas de las colas
celery_app.conf.task_routes = {
    "tasks.generar_manifest": {"queue": "manifest"},
    "worker.tasks.unir_audio": {"queue": "uniones_audio"},
    "worker.tasks.unir_video": {"queue": "uniones_video"},
    "worker.tasks.unir_video2": {"queue": "videos2"},
}

# ⭐ Configuración general
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Monterrey",
    enable_utc=False,
)
