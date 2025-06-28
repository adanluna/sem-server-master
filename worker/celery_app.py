import os
from dotenv import load_dotenv
from celery import Celery

# Cargar variables desde el archivo .env
load_dotenv()

# Configuración desde .env
BROKER_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RESULT_BACKEND = os.getenv(
    "RESULT_BACKEND", "db+postgresql://postgres:postgres@db/forense_db")

# Inicializar Celery
app = Celery('worker',
             broker=BROKER_URL,
             backend=RESULT_BACKEND,
             include=['worker.convertir_video', 'worker.transcribir_audio'])  # Más modular

# Definir rutas de tareas
app.conf.task_routes = {
    "worker.convertir_video.convertir_video": {"queue": "conversiones_video"},
    "worker.transcribir_audio.transcribir_audio": {"queue": "transcripciones"}
}
