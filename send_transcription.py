from celery import Celery
from celery.result import AsyncResult
from dotenv import load_dotenv
import os
import time

# Cargar variables del entorno
load_dotenv()

# Configuración de RabbitMQ y Celery
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RESULT_BACKEND = os.getenv("RESULT_BACKEND", "rpc://")
QUEUE_TASK_TRANSCRIPCION = os.getenv(
    "QUEUE_TASK_TRANSCRIPCION", "tasks.transcribir")
QUEUE_NAME_TRANSCRIPCIONES = os.getenv(
    "QUEUE_NAME_TRANSCRIPCIONES", "transcripciones")
FILENAME = "forense.m4a"  # Solo el nombre base

# Inicializar Celery con backend
app = Celery('client', broker=RABBITMQ_URL, backend=RESULT_BACKEND)

# Enviar tarea a Celery
result = app.send_task(QUEUE_TASK_TRANSCRIPCION, args=[
                       FILENAME], queue=QUEUE_NAME_TRANSCRIPCIONES)

if result:
    print(f"📨 Tarea enviada para transcribir: {FILENAME}")
    print(f"🆔 ID de la tarea: {result.id}")

    # Monitorear resultado sin bloquear la ejecución
    async_res = AsyncResult(result.id, app=app)

    while not async_res.ready():
        print(f"⏳ Transcribiendo {FILENAME}...")
        time.sleep(2)

    print(f"✅ Resultado: {async_res.get()}")
else:
    print("❌ Error al enviar la tarea a Celery.")
