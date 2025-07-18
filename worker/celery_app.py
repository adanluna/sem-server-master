import os
from dotenv import load_dotenv
from celery import Celery

# ✅ Cargar variables de entorno desde .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)
print(f"⚙️ .env cargado desde {env_path}")

# ✅ RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
print(f"🚀 Celery conectando a RabbitMQ: {RABBITMQ_URL}")

# ✅ PostgreSQL backend para resultados
DB_USER = os.getenv('DB_USER', 'semefo_user')
DB_PASS = os.getenv('DB_PASS', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'semefo')

RESULT_BACKEND = f"db+postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(f"💾 Celery backend en PostgreSQL: {DB_HOST}:{DB_PORT}/{DB_NAME}")

# ✅ Crear instancia Celery
celery_app = Celery(
    'worker',
    broker=RABBITMQ_URL,
    backend=RESULT_BACKEND,
    include=[
        'worker.tasks'
    ]
)

# ✅ Configuración avanzada: rutas de tareas a colas específicas
celery_app.conf.task_routes = {
    "worker.tasks.unir_audio": {"queue": "uniones_audio"},
    "worker.tasks.unir_video": {"queue": "uniones_video"},
    "worker.tasks.transcribir_audio": {"queue": "transcripciones_audio"},
}

# ✅ Reintentos automáticos si el broker está inactivo al arrancar
celery_app.conf.broker_connection_retry_on_startup = True
