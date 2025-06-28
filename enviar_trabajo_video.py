from celery import Celery
from celery.result import AsyncResult
from dotenv import load_dotenv
import os
import time
import sys

# Cargar variables de entorno desde el archivo .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Configuración de Celery con RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RESULT_BACKEND = os.getenv("RESULT_BACKEND", "rpc://")
QUEUE_TASK = "worker.convertir_video.convertir_video"
QUEUE_NAME = "conversiones_video"

# Inicializar Celery con backend habilitado
app = Celery('client', broker=RABBITMQ_URL, backend=RESULT_BACKEND)

archivo = "video_prueba.avi"

# Enviar tarea a Celery
result = app.send_task(QUEUE_TASK, args=[archivo], queue=QUEUE_NAME)

print(f"📨 Tarea enviada para convertir: {archivo}")
print(f"🆔 ID de la tarea: {result.id}")

# Esperar resultado sin bloquear la ejecución
async_res = AsyncResult(result.id, app=app)

while not async_res.ready():
    sys.stdout.write(f'\r⏳ Procesando {archivo}...')
    sys.stdout.flush()
    time.sleep(2)

print(f"\n✅ Resultado: {async_res.get()}")
