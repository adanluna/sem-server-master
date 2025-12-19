# ============================================================
#   celery_app.py (FINAL SEMEFO)
#   Configuración oficial del sistema
#   Master server (172.31.82.2)
#
#   - Sin tarea unir_audio (ya no existe en el sistema)
#   - Rutas de colas para manifest, video1, video2
#   - Backend en PostgreSQL
#   - Broker desde RABBITMQ_URL
# ============================================================

from celery import Celery
import os

# ============================================================
#   BROKER / BACKEND
# ============================================================

# Debe provenir SIEMPRE del .env
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
        "worker.manifest_builder"
    ]
)

# ============================================================
#   DEFINICIÓN DE COLAS OFICIALES
# ============================================================

celery_app.conf.task_routes = {
    # manifest builder
    "tasks.generar_manifest": {"queue": "manifest"},

    # unir video principal
    "worker.tasks.unir_video": {"queue": "uniones_video"},

    # unir video secundario
    "worker.tasks.unir_video2": {"queue": "uniones_video"},
}

# ============================================================
#   CONFIGURACIÓN GENERAL
# ============================================================

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Zona horaria del proyecto SEMEFO
    timezone="America/Monterrey",
    enable_utc=False,
)

# ============================================================
#   FIN DEL ARCHIVO
# ============================================================
