# ============================================================
#   celery_app.py (FINAL – LIMPIO Y CORRECTO)
# ============================================================

from celery import Celery
from kombu import Queue
import os

# ============================================================
#   BROKER / BACKEND
# ============================================================

BROKER_URL = os.getenv("RABBITMQ_URL")

RESULT_BACKEND = (
    f"db+postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# ============================================================
#   CREACIÓN DE CELERY
# ============================================================

celery_app = Celery(
    "worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "worker.tasks",
        "worker.manifest_builder",
    ]
)

# ============================================================
#   RUTEO DE TAREAS → COLAS
# ============================================================

celery_app.conf.task_routes = {
    # manifest
    "tasks.generar_manifest": {"queue": "manifest"},

    # video principal
    "worker.tasks.unir_video": {"queue": "uniones_video"},

    # video secundario
    "worker.tasks.unir_video2": {"queue": "uniones_video"},
}

celery_app.conf.task_default_queue = "default"

celery_app.conf.task_queues = (
    Queue("default", durable=True),
    Queue("manifest", durable=True),
    Queue("uniones_video", durable=True),
)

# ============================================================
#   CONFIG GENERAL
# ============================================================

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    timezone="America/Monterrey",
    enable_utc=False,

    # ============================================================
    #   ROBUSTEZ CRÍTICA (NO PERDER TRABAJOS EN REINICIOS)
    # ============================================================
    task_acks_late=True,                 # ACK hasta terminar
    task_reject_on_worker_lost=True,     # si el worker muere -> re-encolar
    # no acaparar mensajes (más justo y seguro)
    worker_prefetch_multiplier=1,

    # (recomendado) si algo se cuelga
    task_soft_time_limit=60 * 60 * 6,    # 6h soft (ajusta a tu máximo real)
    task_time_limit=60 * 60 * 7,         # 7h hard (mata si se pasa)

    task_default_delivery_mode=2,  # persistent

    broker_connection_retry_on_startup=True,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    broker_transport_options={"visibility_timeout": 60 * 60 * 8},
)
