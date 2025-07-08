import os
from dotenv import load_dotenv
from celery import Celery

# Cargar variables desde el .env o el sistema
load_dotenv()

BROKER_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RESULT_BACKEND = os.getenv(
    "RESULT_BACKEND", "db+postgresql://postgres:postgres@db/forense_db")

# Solo manejas video en este servidor

app = Celery('worker',
             broker=BROKER_URL,
             backend=RESULT_BACKEND,
             include=['convertir_video'])

app.conf.task_routes = {
    "convertir_video.convertir_video": {"queue": "conversiones_video"}
}
app.conf.broker_connection_retry_on_startup = True
