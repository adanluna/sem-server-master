# worker/celery_app.py
import os
from dotenv import load_dotenv
from celery import Celery

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

# Detectar si estamos dentro de Docker
IS_DOCKER = os.getenv("IS_DOCKER", "0") == "1"

# Seleccionar el broker correcto
if IS_DOCKER:
    broker_url = os.getenv("RABBITMQ_URL_DOCKER")
else:
    broker_url = os.getenv("RABBITMQ_URL_LOCAL")

# Configurar backend
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
result_backend = f"db+postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# Instancia Celery
celery_app = Celery(
    "worker",
    broker=broker_url,
    backend=result_backend,
    include=["worker.tasks"]
)

celery_app.conf.task_routes = {
    "worker.tasks.unir_audio": {"queue": "uniones_audio"},
    "worker.tasks.unir_video": {"queue": "uniones_video"},
    "worker.tasks.transcribir_audio": {"queue": "transcripciones_audio"},
    "worker.tasks.unir_video2": {"queue": "videos2"},
}

celery_app.conf.broker_connection_retry_on_startup = True
