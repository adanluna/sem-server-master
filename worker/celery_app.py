# ============================================================
#   celery_app.py (FINAL – LIMPIO Y CORRECTO)
# ============================================================

from celery import Celery
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
    # 🔁 REANUDAR TAREAS SI WORKER MUERE / SE REINICIA
    # ============================================================
    task_acks_late=True,              # ACK hasta que termine la tarea
    task_reject_on_worker_lost=True,  # si el worker muere → reencolar
    worker_prefetch_multiplier=1,     # no acaparar tareas
    task_default_delivery_mode=2,     # mensajes persistentes en RabbitMQ
)
