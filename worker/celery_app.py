import os
from dotenv import load_dotenv
from celery import Celery

load_dotenv()

BROKER_URL = os.getenv("RABBITMQ_URL")
RESULT_BACKEND = (
    f"db+postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

celery_app = Celery(
    'worker',
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        'worker.convertir_video',
        'worker.tasks'
    ]
)

celery_app.conf.task_routes = {
    "worker.convertir_video.convertir_video": {"queue": "conversiones_video"},
    "worker.tasks.unir_audio": {"queue": "uniones_audio"},
    "worker.tasks.unir_video": {"queue": "uniones_video"},
    "worker.tasks.transcribir_audio": {"queue": "transcripciones_audio"},
}
celery_app.conf.broker_connection_retry_on_startup = True
